import ast
import re
import math
import matplotlib.pyplot as plt

# ----- Mathematical Probability Operations -----

def gf_add(dist1, dist2):
    """Convolve two distributions (sum of independent probabilities)."""
    new_dist = {}
    for a, pa in dist1.items():
        for b, pb in dist2.items():
            new_dist[a + b] = new_dist.get(a + b, 0) + pa * pb
    return new_dist

def gf_repeat(dist, times):
    """Repeat convolution of a distribution for 'times' iterations."""
    result = {0: 1}  # Identity element for convolution
    for _ in range(times):
        result = gf_add(result, dist)
    return result

def gf_dice(notation):
    """Convert a dice notation (e.g. '1d6') into a probability distribution."""
    m = re.fullmatch(r'(\d+)d(\d+)', notation)
    if not m:
        raise ValueError("Invalid dice notation: " + notation)
    N = int(m.group(1))
    M = int(m.group(2))
    one_die = {i: 1 / M for i in range(1, M + 1)}
    return GF(gf_repeat(one_die, N))

def gf_conditional(gf_obj, condition, replacement):
    """Replace outcomes in gf_obj that satisfy condition with replacement.
    
    If replacement is not already a GF, it is wrapped as a constant distribution.
    """
    prob_replace = sum(prob for outcome, prob in gf_obj.dist.items() if condition(outcome))
    new_dist = {outcome: prob for outcome, prob in gf_obj.dist.items() if not condition(outcome)}
    if not isinstance(replacement, GF):
        replacement = GF({replacement: 1})
    for outcome, prob in replacement.dist.items():
        new_dist[outcome] = new_dist.get(outcome, 0) + prob_replace * prob
    return GF(new_dist)

def gf_if_else(gf_obj, condition, then_replacement, else_replacement):
    """Map outcomes of gf_obj to then_replacement if condition(outcome) is True,
    or else_replacement otherwise.
    
    The replacements can be constants or GF objects.
    """
    # Wrap replacements if needed.
    if not isinstance(then_replacement, GF):
        then_replacement = GF({then_replacement: 1})
    if not isinstance(else_replacement, GF):
        else_replacement = GF({else_replacement: 1})
    p_true = sum(prob for outcome, prob in gf_obj.dist.items() if condition(outcome))
    p_false = 1 - p_true
    new_dist = {}
    for val, prob in then_replacement.dist.items():
        new_dist[val] = new_dist.get(val, 0) + p_true * prob
    for val, prob in else_replacement.dist.items():
        new_dist[val] = new_dist.get(val, 0) + p_false * prob
    return GF(new_dist)

class GF:
    """A class representing a probability distribution."""
    def __init__(self, dist):
        self.dist = dist

    def __add__(self, other):
        if isinstance(other, GF):
            return GF(gf_add(self.dist, other.dist))
        elif isinstance(other, int):
            return GF({k + other: v for k, v in self.dist.items()})
        else:
            return NotImplemented

    def __radd__(self, other):
        if isinstance(other, int):
            return GF({k + other: v for k, v in self.dist.items()})
        return NotImplemented

    def __sub__(self, other):
        if isinstance(other, int):
            return GF({k - other: v for k, v in self.dist.items()})
        elif isinstance(other, GF):
            reflected = { -k: v for k, v in other.dist.items() }
            return GF(gf_add(self.dist, reflected))
        else:
            return NotImplemented

    def __rsub__(self, other):
        if isinstance(other, int):
            return GF({other - k: v for k, v in self.dist.items()})
        return NotImplemented

    def __mul__(self, other):
        if isinstance(other, int):
            return GF(gf_repeat(self.dist, other))
        return NotImplemented

    def __rmul__(self, other):
        if isinstance(other, int):
            return GF(gf_repeat(self.dist, other))
        return NotImplemented

    def __str__(self):
        return str(self.dist)
    __repr__ = __str__

# ----- Extended AST Transformer -----

class DiceTransformer(ast.NodeTransformer):
    """
    Transforms dice syntax into mathematical probability computations.
    
    Supports:
    
    Pattern A (if with same variable):
        x = 1d6
        if x < 3:
            x = 1d6
        result = x
        
    Pattern B (if with different target for conditional assignment):
        x = 1d6
        if x < 3:
            result = 7
        result = x
        
    Pattern C (if/else with same variable):
        x = 1d6
        if x == 3:
            x = 10
        else:
            x = 20
        result = x
        
    The transformer converts these into calls to gf_conditional (for if-only)
    or gf_if_else (for if/else).
    """
    def __init__(self):
        self.conditional_assignments = {}  # For Pattern B
        super().__init__()

    def visit_If(self, node):
        # If/else branch (Pattern C)
        if (node.orelse and len(node.body) == 1 and len(node.orelse) == 1 and
            isinstance(node.test, ast.Compare) and
            isinstance(node.test.left, ast.Name) and
            len(node.test.ops) == 1 and
            isinstance(node.test.ops[0], (ast.Eq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.NotEq)) and
            isinstance(node.test.comparators[0], ast.Constant) and
            isinstance(node.body[0], ast.Assign) and len(node.body[0].targets) == 1 and
            isinstance(node.orelse[0], ast.Assign) and len(node.orelse[0].targets) == 1):
            
            var = node.test.left.id
            # For if/else, we require that both branches assign to the same variable.
            then_target = node.body[0].targets[0].id
            else_target = node.orelse[0].targets[0].id
            if then_target == else_target == var:
                # Transform into: var = gf_if_else(var, lambda outcome: <condition>, then_expr, else_expr)
                new_lambda = ast.Lambda(
                    args=ast.arguments(
                        args=[ast.arg(arg="outcome")],
                        posonlyargs=[], defaults=[]),
                    body=ast.Compare(
                        left=ast.Name(id="outcome", ctx=ast.Load()),
                        ops=node.test.ops,
                        comparators=node.test.comparators
                    )
                )
                then_expr = node.body[0].value
                else_expr = node.orelse[0].value
                new_call = ast.Call(
                    func=ast.Name(id="gf_if_else", ctx=ast.Load()),
                    args=[
                        ast.Name(id=var, ctx=ast.Load()),
                        new_lambda,
                        then_expr,
                        else_expr
                    ],
                    keywords=[]
                )
                return ast.Assign(
                    targets=[ast.Name(id=var, ctx=ast.Store())],
                    value=new_call
                )
        # If only branch (Pattern A or B)
        if (isinstance(node.test, ast.Compare) and
            isinstance(node.test.left, ast.Name) and
            len(node.test.ops) == 1 and
            isinstance(node.test.ops[0], (ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq)) and
            len(node.test.comparators) == 1 and
            isinstance(node.test.comparators[0], ast.Constant) and
            len(node.body) == 1 and
            isinstance(node.body[0], ast.Assign) and
            len(node.body[0].targets) == 1 and
            isinstance(node.body[0].targets[0], ast.Name)):
            
            source_var = node.test.left.id
            compare_op = node.test.ops[0]
            compare_val = node.test.comparators[0]
            target = node.body[0].targets[0].id
            alt_expr = node.body[0].value
            # Pattern A: target == source_var → transform immediately.
            if target == source_var:
                new_lambda = ast.Lambda(
                    args=ast.arguments(
                        args=[ast.arg(arg="outcome")],
                        posonlyargs=[], defaults=[]),
                    body=ast.Compare(
                        left=ast.Name(id="outcome", ctx=ast.Load()),
                        ops=[compare_op],
                        comparators=[compare_val]
                    )
                )
                new_call = ast.Call(
                    func=ast.Name(id="gf_conditional", ctx=ast.Load()),
                    args=[ast.Name(id=source_var, ctx=ast.Load()), new_lambda, alt_expr],
                    keywords=[]
                )
                return ast.Assign(
                    targets=[ast.Name(id=source_var, ctx=ast.Store())],
                    value=new_call
                )
            else:
                # Pattern B: store the conditional for later merging.
                self.conditional_assignments[target] = (source_var, compare_op, compare_val, alt_expr)
                return ast.Pass()
        return self.generic_visit(node)

    def visit_Assign(self, node):
        # Merge stored conditionals for Pattern B.
        if (len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and
            isinstance(node.value, ast.Name)):
            target = node.targets[0].id
            source = node.value.id
            if target in self.conditional_assignments:
                stored_source, op, const_node, alt_expr = self.conditional_assignments[target]
                if source == stored_source:
                    new_lambda = ast.Lambda(
                        args=ast.arguments(
                            args=[ast.arg(arg="outcome")],
                            posonlyargs=[], defaults=[]),
                        body=ast.Compare(
                            left=ast.Name(id="outcome", ctx=ast.Load()),
                            ops=[op],
                            comparators=[const_node]
                        )
                    )
                    new_call = ast.Call(
                        func=ast.Name(id="gf_conditional", ctx=ast.Load()),
                        args=[ast.Name(id=source, ctx=ast.Load()), new_lambda, alt_expr],
                        keywords=[]
                    )
                    return ast.copy_location(
                        ast.Assign(targets=[ast.Name(id=target, ctx=ast.Store())], value=new_call),
                        node
                    )
        return self.generic_visit(node)

def preprocess_code(code):
    """Replace dice literals like '1d6' with valid function calls."""
    return re.sub(r'(\b\d+d\d+\b)', r'gf_dice("\1")', code)

# ----- Main Execution -----

def main():
    # Configuration variables
    DECIMAL_POINTS = 2        # Number of decimal places for probability labels
    MIN_LABEL_PERCENT = 1.0   # Do not display labels for probabilities below this percent
    SHOW_CONFIDENCE_INTERVALS = True  # Toggle to show confidence interval bounds on the plot
    CONFIDENCE_LEVEL = 0.90     # Confidence interval level (e.g., 0.90 for 90% or 0.95 for 95%)

    # Read dice code from external file "code.txt"
    try:
        with open("code.txt", "r") as f:
            code = f.read()
    except FileNotFoundError:
        print("Error: 'code.txt' not found.")
        return

    # Preprocess and transform the code
    processed_code = preprocess_code(code)
    tree = ast.parse(processed_code)
    transformer = DiceTransformer()
    tree = transformer.visit(tree)
    ast.fix_missing_locations(tree)

    # Execute the transformed code in our custom environment
    env = {"gf_dice": gf_dice, "gf_conditional": gf_conditional, "gf_if_else": gf_if_else, "GF": GF}
    exec(compile(tree, "<ast>", "exec"), env)

    # Retrieve the resulting distribution from variable 'result'
    if "result" not in env:
        print("Error: No variable named 'result' found in the code.")
        return
    result = env["result"]
    outcomes, probabilities = zip(*sorted(result.dist.items()))
    
    # Create the bar plot for the probability distribution
    fig, ax = plt.subplots()
    bars = ax.bar(outcomes, [p * 100 for p in probabilities],
                  color="skyblue", edgecolor="black")
    for bar, p in zip(bars, probabilities):
        percent_value = p * 100
        if percent_value >= MIN_LABEL_PERCENT:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2., 
                height,
                f'{percent_value:.{DECIMAL_POINTS}f}%',
                ha='center', 
                va='bottom'
            )
    ax.set_xlabel("Outcome")
    ax.set_ylabel("Probability (%)")
    ax.set_title("Distribution for result")
    ax.set_xticks(outcomes)
    
    # Confidence Interval Calculation and Display
    if SHOW_CONFIDENCE_INTERVALS:
        sorted_outcomes = sorted(result.dist.keys())
        cum_prob = 0
        lower_bound = None
        upper_bound = None
        lower_target = (1 - CONFIDENCE_LEVEL) / 2
        upper_target = 1 - lower_target
        
        for outcome in sorted_outcomes:
            cum_prob += result.dist[outcome]
            if lower_bound is None and cum_prob >= lower_target:
                lower_bound = outcome
            if cum_prob >= upper_target:
                upper_bound = outcome
                break

        ax.axvline(x=lower_bound, color='red', linestyle='--', 
                   label=f'Lower {CONFIDENCE_LEVEL*100:.0f}% bound')
        ax.axvline(x=upper_bound, color='green', linestyle='--', 
                   label=f'Upper {CONFIDENCE_LEVEL*100:.0f}% bound')
        ax.legend()
        print(f"{CONFIDENCE_LEVEL*100:.0f}% confidence interval: [{lower_bound}, {upper_bound}]")
    
    # ----- Summary Statistics (printed to terminal) -----
    mean_val = sum(x * p for x, p in result.dist.items())
    variance_val = sum(p * (x - mean_val)**2 for x, p in result.dist.items())
    std_val = math.sqrt(variance_val)
    sorted_outcomes = sorted(result.dist.keys())
    cum_prob = 0
    median_val = None
    for x in sorted_outcomes:
        cum_prob += result.dist[x]
        if cum_prob >= 0.5:
            median_val = x
            break
    min_val = sorted_outcomes[0]
    max_val = sorted_outcomes[-1]
    
    summary_data = [
        ["Median", f"{median_val:.{DECIMAL_POINTS}f}"],
        ["Mean", f"{mean_val:.{DECIMAL_POINTS}f}"],
        ["Std Dev", f"{std_val:.{DECIMAL_POINTS}f}"],
        ["Minimum", f"{min_val:.{DECIMAL_POINTS}f}"],
        ["Maximum", f"{max_val:.{DECIMAL_POINTS}f}"],
    ]
    
    print("Summary Statistics:")
    for stat, value in summary_data:
        print(f"{stat}: {value}")
    
    plt.show()

if __name__ == "__main__":
    main()
