from collections import defaultdict

class Node:
    """
    Base node for Huffman tree.
    """
    def __init__(self):
        self.parent = None
        self.side = None  # 0 = left, 1 = right
        self.weight = 0

    def __lt__(self, other):
        return self.weight < other.weight

class LeafNode(Node):
    """
    A leaf node with a symbol value.
    """
    def __init__(self, value: int, weight: int):
        super().__init__()
        self.value = value
        self.weight = weight

    def __repr__(self):
        return f"Leaf({self.value}:{self.weight})"

class InternalNode(Node):
    """
    An internal node with left and right children.
    """
    def __init__(self, left: Node, right: Node):
        super().__init__()
        left.parent = self
        left.side = 0
        right.parent = self
        right.side = 1
        self.left = left
        self.right = right
        self.weight = left.weight + right.weight

    def __repr__(self):
        return f"Internal({self.left}, {self.right})"

class HuffmanTree:
    """
    Builds a canonical Huffman tree with depth limit.
    """
    def __init__(self, freqs: list[int], limit: int):
        self.num_symbols = len(freqs)
        self.limit = limit
        self.depth_map: dict[int, list[LeafNode]] = {}
        self.max_depth = 0
        # Create initial leaf nodes
        queue = []
        for sym, wt in enumerate(freqs):
            if wt > 0:
                queue.append(LeafNode(sym, wt))
        # ensure at least two leaves
        idx = 0
        while len(queue) < 2:
            if freqs[idx] == 0:
                queue.append(LeafNode(idx, 1))
            idx += 1
        # build by repeatedly merging smallest
        queue.sort()
        while len(queue) > 1:
            left = queue.pop(0)
            right = queue.pop(0)
            queue.append(InternalNode(left, right))
            queue.sort()
        self.root = queue[0]
        # traverse and balance
        self._traverse()
        self._balance()

    def _traverse(self):
        self.depth_map.clear()
        self.max_depth = 0
        self._traverse_node(self.root, 0)

    def _traverse_node(self, node: Node, depth: int):
        if depth > self.max_depth:
            self.max_depth = depth
        if isinstance(node, InternalNode):
            self._traverse_node(node.left, depth+1)
            self._traverse_node(node.right, depth+1)
        else:
            self.depth_map.setdefault(depth, []).append(node)

    def _balance(self):
        # enforce depth limit
        while self.max_depth > self.limit:
            # pick a leaf too deep
            over = self.depth_map.get(self.max_depth, [])
            if not over:
                break
            leafA = over[0]
            parent1 = leafA.parent
            # opposite sibling
            leafB = parent1.right if leafA.side == 0 else parent1.left
            parent2 = parent1.parent
            # replace leafA with leafB at parent2
            if parent1.side == 0:
                parent2.left = leafB
                leafB.parent = parent2; leafB.side = 0
            else:
                parent2.right = leafB
                leafB.parent = parent2; leafB.side = 1
            # try inserting leafA under a shallower leafC
            moved = False
            for d in range(self.max_depth-2, 0, -1):
                leaves = self.depth_map.get(d)
                if leaves:
                    leafC = leaves[0]
                    parent3 = leafC.parent
                    if leafC.side == 0:
                        parent3.left = InternalNode(leafA, leafC)
                        parent3.left.parent = parent3; parent3.left.side = 0
                    else:
                        parent3.right = InternalNode(leafA, leafC)
                        parent3.right.parent = parent3; parent3.right.side = 1
                    moved = True
                    break
            if not moved:
                break
            self._traverse()

    def get_table(self) -> 'HuffmanTable':
        # generate canonical codes from depth_map
        table = HuffmanTable(self.num_symbols)
        code = table.code
        codelen = table.code_len
        next_code = 0
        last_shift = 0
        for length in sorted(self.depth_map):
            next_code <<= (length - last_shift)
            last_shift = length
            leaves = sorted(self.depth_map[length], key=lambda n: n.value)
            for leaf in leaves:
                code[leaf.value] = next_code
                codelen[leaf.value] = length
                next_code += 1
        return table

class HuffmanTable:
    """
    Stores codes and lengths, and can pack them per RFC1951.
    """
    def __init__(self, num_symbols: int):
        self.code = [0] * num_symbols
        self.code_len = [0] * num_symbols

    @staticmethod
    def pack_code_lengths(lit_len: list[int], dist_len: list[int]) -> list[int]:
        lengths = []
        HuffmanTable._run_pack(lengths, lit_len)
        HuffmanTable._run_pack(lengths, dist_len)
        return lengths

    @staticmethod
    def _run_pack(lengths: list[int], code_len: list[int]):
        n = len(code_len)
        last = code_len[0]
        run = 1
        for i in range(1, n+1):
            same = (i < n and code_len[i] == last)
            if same:
                run += 1
            else:
                lengths.append(last)
                run -= 1
                if last == 0:
                    # runs of zeros
                    while run >= 138:
                        lengths += [18, 138-11]
                        run -= 138
                    while run >= 11:
                        lengths += [18, run-11]
                        run = 0
                    while run >= 3:
                        lengths += [17, run-3]
                        run -= 3
                else:
                    while run >= 3:
                        lengths += [16, run-3]
                        run -= 3
                while run > 0:
                    lengths.append(last)
                    run -= 1
                if i < n:
                    last = code_len[i]; run = 1

        # Після визначення класу HuffmanTable:

    def _generate_canonical_codes(code_len: list[int]) -> list[int]:
        """Повертає список кодів за канонічною схемою зі списку довжин."""
        lengths = sorted(set(filter(lambda x: x>0, code_len)))
        code = 0
        last_len = 0
        next_code: dict[int,int] = {}
        for length in lengths:
            code <<= (length - last_len)
            next_code[length] = code
            last_len = length
            code += code_len.count(length)
        codes = [0] * len(code_len)
        for sym, length in enumerate(code_len):
            if length > 0:
                codes[sym] = next_code[length]
                next_code[length] += 1
        return codes

    def _make_fixed_tables():
        # 1) Створюємо масив довжин для літералів/довжин
        lit_len = [0]*286
        for i in range(0, 144):  lit_len[i] = 8
        for i in range(144,256): lit_len[i] = 9
        for i in range(256,280): lit_len[i] = 7
        for i in range(280,286): lit_len[i] = 8

        # 2) Масив довжин для дистанцій
        dist_len = [5]*30

        # 3) Генеруємо коди канонічно
        lit_tbl  = HuffmanTable(len(lit_len))
        lit_tbl.code_len = lit_len
        lit_tbl.code     = _generate_canonical_codes(lit_len)

        dist_tbl = HuffmanTable(len(dist_len))
        dist_tbl.code_len = dist_len
        dist_tbl.code     = _generate_canonical_codes(dist_len)

        return lit_tbl, dist_tbl
    HuffmanTable.LIT, HuffmanTable.DIST = _make_fixed_tables()

    LIT = HuffmanTable(286)
    DIST = HuffmanTable(30)