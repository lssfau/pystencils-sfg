from __future__ import annotations
from textwrap import indent

from pystencils.backend.emission import CAstPrinter

from ..ir import (
    SfgSourceFile,
    SfgSourceFileType,
    SfgNamespaceBlock,
    SfgEntityDecl,
    SfgEntityDef,
    SfgKernelHandle,
    SfgFunction,
    SfgClassMember,
    SfgMethod,
    SfgMemberVariable,
    SfgConstructor,
    SfgClass,
    SfgClassBody,
    SfgVisibilityBlock,
    SfgVisibility,
)
from ..ir.syntax import SfgNamespaceElement, SfgClassBodyElement
from ..config import CodeStyle


class SfgFilePrinter:
    def __init__(self, code_style: CodeStyle) -> None:
        self._code_style = code_style
        self._kernel_printer = CAstPrinter(
            indent_width=code_style.get_option("indent_width")
        )

    def __call__(self, file: SfgSourceFile) -> str:
        code = ""

        if file.prelude:
            comment = "/**\n"
            comment += indent(file.prelude, " * ", predicate=lambda _: True)
            comment += " */\n\n"

            code += comment

        if file.file_type == SfgSourceFileType.HEADER:
            code += "#pragma once\n\n"

        for header in file.includes:
            incl = str(header) if header.system_header else f'"{str(header)}"'
            code += f"#include {incl}\n"

        if file.includes:
            code += "\n"

        #   Here begins the actual code
        code += "\n\n".join(self.visit(elem) for elem in file.elements)
        code += "\n"

        return code

    def visit(
        self, elem: SfgNamespaceElement | SfgClassBodyElement, inclass: bool = False
    ) -> str:
        match elem:
            case str():
                return elem
            case SfgNamespaceBlock(_, elements, label):
                code = f"namespace {label} {{\n"
                code += self._code_style.indent(
                    "\n\n".join(self.visit(e) for e in elements)
                )
                code += f"\n}} // namespace {label}"
                return code
            case SfgEntityDecl(entity):
                return self.visit_decl(entity, inclass)
            case SfgEntityDef(entity):
                return self.visit_defin(entity, inclass)
            case SfgClassBody():
                return self.visit_defin(elem, inclass)
            case _:
                assert False, "illegal code element"

    def visit_decl(
        self,
        declared_entity: SfgKernelHandle | SfgFunction | SfgClassMember | SfgClass,
        inclass: bool = False,
    ) -> str:
        match declared_entity:
            case SfgKernelHandle(kernel):
                return self._kernel_printer.print_signature(kernel) + ";"

            case SfgFunction(name, _, params) | SfgMethod(name, _, params):
                return self._func_signature(declared_entity, inclass) + ";"

            case SfgConstructor(cls, params):
                params_str = ", ".join(
                    f"{param.dtype.c_string()} {param.name}" for param in params
                )
                return f"{cls.name}({params_str});"

            case SfgMemberVariable(name, dtype):
                return f"{dtype.c_string()} {name};"

            case SfgClass(kwd, name):
                return f"{str(kwd)} {name};"

            case _:
                assert False, f"unsupported declared entity: {declared_entity}"

    def visit_defin(
        self,
        defined_entity: SfgKernelHandle | SfgFunction | SfgClassMember | SfgClassBody,
        inclass: bool = False,
    ) -> str:
        match defined_entity:
            case SfgKernelHandle(kernel):
                return self._kernel_printer(kernel)

            case SfgFunction(name, tree, params) | SfgMethod(name, tree, params):
                sig = self._func_signature(defined_entity, inclass)
                body = tree.get_code(self._code_style)
                body = "\n{\n" + self._code_style.indent(body) + "\n}"
                return sig + body

            case SfgConstructor(cls, params):
                params_str = ", ".join(
                    f"{param.dtype.c_string()} {param.name}" for param in params
                )

                code = ""
                if not inclass:
                    code += f"{cls.name}::"
                code += f"{cls.name} ({params_str})"

                inits: list[str] = []
                for var, args in defined_entity.initializers:
                    args_str = ", ".join(str(arg) for arg in args)
                    inits.append(f"{str(var)}({args_str})")

                if inits:
                    code += "\n:" + ",\n".join(inits)

                code += "\n{\n" + self._code_style.indent(defined_entity.body) + "\n}"
                return code

            case SfgMemberVariable(name, dtype):
                code = dtype.c_string()
                if not inclass:
                    code += f" {defined_entity.owning_class.name}::"
                code += f" {name}"
                if defined_entity.default_init is not None:
                    args_str = ", ".join(
                        str(expr) for expr in defined_entity.default_init
                    )
                    code += "{" + args_str + "}"
                code += ";"
                return code

            case SfgClassBody(cls, vblocks):
                code = f"{cls.class_keyword} {cls.name}"
                if cls.base_classes:
                    code += " : " + ", ".join(cls.base_classes)
                code += " {\n"
                vblocks_str = [self._visibility_block(b) for b in vblocks]
                code += "\n\n".join(vblocks_str)
                code += "\n};\n"
                return code

            case _:
                assert False, f"unsupported defined entity: {defined_entity}"

    def _visibility_block(self, vblock: SfgVisibilityBlock):
        prefix = (
            f"{vblock.visibility}:\n"
            if vblock.visibility != SfgVisibility.DEFAULT
            else ""
        )
        elements = [self.visit(elem, inclass=True) for elem in vblock.elements]
        return prefix + self._code_style.indent("\n".join(elements))

    def _func_signature(self, func: SfgFunction | SfgMethod, inclass: bool):
        code = ""

        if func.attributes:
            code += "[[" + ", ".join(func.attributes) + "]]"

        if func.inline and not inclass:
            code += "inline "

        if isinstance(func, SfgMethod) and inclass:
            if func.static:
                code += "static "
            if func.virtual:
                code += "virtual "

        if func.constexpr:
            code += "constexpr "

        code += func.return_type.c_string() + " "
        params_str = ", ".join(
            f"{param.dtype.c_string()} {param.name}" for param in func.parameters
        )
        if isinstance(func, SfgMethod) and not inclass:
            code += f"{func.owning_class.name}::"
        code += f"{func.name}({params_str})"

        if isinstance(func, SfgMethod):
            if func.const:
                code += " const"
            if func.override and inclass:
                code += " override"

        return code
