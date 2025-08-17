class SymbolTable:
    # ... A class to manage variables, their types, and stack offsets
    pass

class CodeGenerator:
    def __init__(self):
        self.assembly_code = []
        self.symbol_table = SymbolTable()
        self.label_count = 0

    def new_label(self):
        self.label_count += 1
        return f"L{self.label_count}"

    def generate(self, node):
        self.visit(node)
        return "\n".join(self.assembly_code)

    def visit(self, node):
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        raise NotImplementedError(f"No visit_{type(node).__name__} method")

    def visit_Program(self, node):
        # Basic setup for asez80
        self.assembly_code.append("\t.org 0x100") # Example start address
        self.assembly_code.append("init:")
        self.assembly_code.append("\tld sp, 0xFFFE ; Setup stack pointer")
        # In a full compiler, we'd call a 'main' function
        # For now, just execute global statements
        for child in node.children:
            self.visit(child)
        self.assembly_code.append("\thalt")
        self.assembly_code.append("\t.end init")

    def visit_VarDecl(self, node):
        var_name = node.var_node.value
        var_type = node.type_node.value
        
        # This is a simplified example for local variables
        # For now, we treat them as globals for simplicity
        # A real implementation would handle stack allocation.
        
        self.assembly_code.append(f"; Variable Declaration for {var_name}")
        if var_type == 'int':
            size = 2 # 16 bits
        elif var_type == 'byte':
            size = 1 # 8 bits
        else:
            raise TypeError(f"Unknown type: {var_type}")

        # In a real compiler, we would add to symbol table with its memory location
        # self.symbol_table.define(var_name, var_type, memory_address)
        
        # Here we just define a label and reserve space in memory
        self.assembly_code.append(f"{var_name}:")
        self.assembly_code.append(f"\t.ds {size}")

    # --- Code Generation for specific features ---
    
    # Example: How `a.3 = 1;` might be compiled
    def visit_BitAssignment(self, node): # Assuming a BitAssignment AST node exists
        # node.variable -> the variable 'a'
        # node.bit_number -> the integer 3
        # node.value -> the value to assign (0 or 1)
        
        var_name = node.variable.value
        bit_num = node.bit_number
        
        # Assume 'a' is a byte variable at a known memory address
        self.assembly_code.append(f"; Bit set for {var_name}.{bit_num}")
        self.assembly_code.append(f"\tld a, ({var_name}) ; Load value of 'a' into accumulator")
        if node.value == 1:
            self.assembly_code.append(f"\tset {bit_num}, a       ; Set bit {bit_num}")
        else:
            self.assembly_code.append(f"\tres {bit_num}, a       ; Reset bit {bit_num}")
        self.assembly_code.append(f"\tld ({var_name}), a ; Store it back")
        
    # Example: How `MEM[0x8000] = 0x21;` might be compiled
    def visit_MemAssignment(self, node): # Assuming a MemAssignment AST node exists
        # node.address -> the expression for the address (e.g., 0x8000)
        # node.value -> the expression for the value (e.g., 0x21)
        
        # 1. Evaluate value and put it in A (for byte)
        # self.visit(node.value) -> result would be in register A
        self.assembly_code.append(f"\tld a, {hex(node.value.integer)}")
        
        # 2. Evaluate address and put it in HL
        # self.visit(node.address) -> result would be in register HL
        self.assembly_code.append(f"\tld hl, {hex(node.address.integer)}")

        # 3. Store A at the address pointed to by HL
        self.assembly_code.append(f"\tld (hl), a ; MEM[addr] = value")