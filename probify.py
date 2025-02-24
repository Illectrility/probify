import ast
import re
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
    """Apply conditional rerolling."""
    prob_replace = sum(prob for outcome, prob in gf_obj.dist.items() if condition(outcome))
    new_dist = {outcome: prob for outcome, prob in gf_obj.dist.items() if not condition(outcome)}
    for outcome, prob in replacement.dist.items():
        new_dist[outcome] = new_dist.get(outcome, 0) + prob_replace * prob
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
        return self + other

    def __mul__(self, other):
        if isinstance(other, int):
            return GF(gf_repeat(self.dist, other))
        return NotImplemented

    def __rmul__(self, other):
        return self * other

    def __str__(self):
        return str(self.dist)

    __repr__ = __str__

# ----- AST Transformation -----

class DiceTransformer(ast.NodeTransformer):
    def visit_If(self, node):
        if (isinstance(node.test, ast.Compare) and
            isinstance(node.test.left, ast.Name) and
            len(node.test.ops) == 1 and
            isinstance(node.test.ops[0], (ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq)) and
            len(node.test.comparators) == 1 and
            isinstance(node.test.comparators[0], ast.Constant)):
            
            var_name = node.test.left.id
            if (len(node.body) == 1 and isinstance(node.body[0], ast.Assign) and
                len(node.body[0].targets) == 1 and isinstance(node.body[0].targets[0], ast.Name) and
                node.body[0].targets[0].id == var_name):
                
                assign_node = node.body[0]
                new_compare = ast.Lambda(
                    args=ast.arguments(
                        args=[ast.arg(arg="outcome")],
                        posonlyargs=[], defaults=[]),
                    body=ast.Compare(
                        left=ast.Name(id="outcome", ctx=ast.Load()),
                        ops=node.test.ops,
                        comparators=node.test.comparators
                    )
                )
                new_call = ast.Call(
                    func=ast.Name(id="gf_conditional", ctx=ast.Load()),
                    args=[ast.Name(id=var_name, ctx=ast.Load()), new_compare, assign_node.value],
                    keywords=[]
                )
                return ast.Assign(targets=[ast.Name(id=var_name, ctx=ast.Store())], value=new_call)
        return self.generic_visit(node)

    def visit_For(self, node):
        # Handles simple loops like: for i in range(6): result += 1d6
        if (isinstance(node.target, ast.Name) and
            isinstance(node.iter, ast.Call) and
            isinstance(node.iter.func, ast.Name) and
            node.iter.func.id == "range" and
            len(node.iter.args) == 1 and
            isinstance(node.iter.args[0], ast.Constant)):
            
            loop_count = node.iter.args[0].value

            if (len(node.body) == 1 and isinstance(node.body[0], ast.AugAssign) and
                isinstance(node.body[0].op, ast.Add) and
                isinstance(node.body[0].target, ast.Name) and
                isinstance(node.body[0].value, ast.Call)):
                
                augassign = node.body[0]
                # Replace loop with multiplication: dice roll * loop_count
                new_call = ast.BinOp(left=augassign.value, op=ast.Mult(), right=ast.Constant(value=loop_count))
                return ast.Assign(
                    targets=[ast.Name(id=augassign.target.id, ctx=ast.Store())],
                    value=ast.BinOp(
                        left=ast.Name(id=augassign.target.id, ctx=ast.Load()),
                        op=ast.Add(),
                        right=new_call
                    )
                )
        return self.generic_visit(node)

def preprocess_code(code):
    """Replace dice literals like '1d6' with valid function calls."""
    return re.sub(r'(\b\d+d\d+\b)', r'gf_dice("\1")', code)

# ----- Main Execution -----

def main():
    # Set the number of decimal points for probability labels.
    DECIMAL_POINTS = 2  # e.g., 2 decimal places
    # Set the minimum percentage threshold below which no label is shown.
    MIN_LABEL_PERCENT = 1.0  # e.g., do not show labels if below 1%

    code = """

result = 6d6
    
"""
    # Preprocess and transform the code
    processed_code = preprocess_code(code)
    tree = ast.parse(processed_code)
    tree = DiceTransformer().visit(tree)
    ast.fix_missing_locations(tree)

    # Execution environment
    env = {"gf_dice": gf_dice, "gf_conditional": gf_conditional, "GF": GF}
    exec(compile(tree, "<ast>", "exec"), env)

    # Retrieve the result distribution from variable 'result'
    result = env["result"]
    outcomes, probabilities = zip(*sorted(result.dist.items()))
    
    # Plot the probability distribution with labels on each bar
    bars = plt.bar(outcomes, [p * 100 for p in probabilities],
                   color="skyblue", edgecolor="black")
    for bar, p in zip(bars, probabilities):
        percent_value = p * 100
        # Only add a label if the probability meets or exceeds MIN_LABEL_PERCENT
        if percent_value >= MIN_LABEL_PERCENT:
            height = bar.get_height()
            plt.text(
                bar.get_x() + bar.get_width() / 2., 
                height,
                f'{percent_value:.{DECIMAL_POINTS}f}%',  # Uses DECIMAL_POINTS for formatting
                ha='center', 
                va='bottom'
            )
    plt.xlabel("Outcome")
    plt.ylabel("Probability (%)")
    plt.title("Distribution for result")
    plt.xticks(outcomes)
    plt.show()

if __name__ == "__main__":
    main()

