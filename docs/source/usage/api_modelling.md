---
file_format: mystnb
kernelspec:
  name: python3
---

(how_to_cpp_api_modelling)=
# How To Reflect C++ APIs

```{code-cell} ipython3
:tags: [remove-cell]

from __future__ import annotations
import sys
from pathlib import Path

mockup_path = Path("../_util").resolve()
sys.path.append(str(mockup_path))

from sfg_monkeypatch import DocsPatchedGenerator  # monkeypatch SFG for docs

from pystencilssfg import SourceFileGenerator
```

Pystencils-SFG is designed to help you generate C++ code that interfaces with pystencils on the one side,
and with your handwritten code on the other side.
This requires that the C++ classes and APIs of your framework or application be represented within the SFG system.
This guide shows how you can use the facilities of the {any}`pystencilssfg.lang` module to model your C++ interfaces
for use with the code generator.

To begin, import the `lang` module:

```{code-cell} ipython3
from pystencilssfg import lang
```

## Defining C++ Types and Type Templates

The first C++ entities that need to be mirrored for the SFGs are the types and type templates a library
or application uses or exposes.

### Non-Templated Types

To define a C++ type, we use {any}`pystencilssfg.lang.cpptype <pystencilssfg.lang.types.cpptype>`:

```{code-cell} ipython3
MyClassTypeFactory = lang.cpptype("my_namespace::MyClass", "MyClass.hpp")
MyClassTypeFactory
```

This defines two properties of the type: its fully qualified name, and the set of headers
that need to be included when working with the type.
Now, whenever this type occurs as the type of a variable given to pystencils-sfg,
the code generator will make sure that `MyClass.hpp` is included into the respective
generated code file.

The object returned by `cpptype` is not the type itself, but a factory for instances of the type.
Even as `MyClass` does not have any template parameters, we can create different instances of it:
`const` and non-`const`, as well as references and non-references.
We do this by calling the factory:

```{code-cell} ipython3
MyClass = MyClassTypeFactory()
str(MyClass)
```

To produce a `const`-qualified version of the type:

```{code-cell} ipython3
MyClassConst = MyClassTypeFactory(const=True)
str(MyClassConst)
```

And finally, to produce a reference instead:

```{code-cell} ipython3
MyClassRef = MyClassTypeFactory(ref=True)
str(MyClassRef)
```

Of course, `const` and `ref` can also be combined to create a reference-to-const.

### Types with Template Parameters

We can add template parameters to our type by the use of
[Python format strings](https://docs.python.org/3/library/string.html#formatstrings):

```{code-cell} ipython3
MyClassTemplate = lang.cpptype("my_namespace::MyClass< {T1}, {T2} >", "MyClass.hpp")
MyClassTemplate
```

Here, the type parameters `T1` and `T2` are specified in braces.
For them, values must be provided when calling the factory to instantiate the type:

```{code-cell} ipython3
MyClassIntDouble = MyClassTemplate(T1="int", T2="double")
str(MyClassIntDouble)
```

The way type parameters are passed to the factory is identical to the behavior of {any}`str.format`,
except that it does not support attribute or element accesses.
In particular, this means that we can also use unnamed, implicit positional parameters:

```{code-cell} ipython3
MyClassTemplate = lang.cpptype("my_namespace::MyClass< {}, {} >", "MyClass.hpp")
MyClassIntDouble = MyClassTemplate("int", "double")
str(MyClassIntDouble)
```

## Creating Variables and Expressions

Type templates and types will not get us far on their own.
To use them in APIs, as function or constructor parameters,
or as class members and local objects,
we need to create *variables* with certain types.

To do so, we need to inject our defined types into the expression framework of pystencils-sfg.
We wrap the type in an interface that allows us to create variables and, later, more complex expressions,
using {any}`lang.CppClass <pystencilssfg.lang.expressions.CppClass>`:

```{code-cell} ipython3
class MyClass(lang.CppClass):
    template = lang.cpptype("my_namespace::MyClass< {T1}, {T2} >", "MyClass.hpp")
```

Instances of `MyClass` can now be created via constructor call, in the same way as above.
This gives us an unbound `MyClass` object, which we can bind to a variable name by calling `var` on it:

```{code-cell} ipython3
my_obj = MyClass(T1="int", T2="void").var("my_obj")
my_obj, str(my_obj.dtype)
```

## Reflecting C++ Class APIs

In the previous section, we showed how to reflect a C++ class in pystencils-sfg in order to create
a variable representing an object of that class.
We can now extend this to reflect the public API of the class, in order to create complex expressions
involving objects of `MyClass` during code generation.

### Public Methods

Assume `MyClass` has the following public interface:

```C++
template< typename T1, typename T2 >
class MyClass {
public:
  T1 & getA();
  std::tuple< T1, T2 > getBoth();

  void replace(T1 a_new, T2 b_new);
}
```

We mirror this in our Python reflection of `CppClass` using methods that create `AugExpr` objects,
which represent C++ expressions annotated with variables they depend on.
A possible implementation might look like this:

```{code-cell} ipython3
---
tags: [remove-cell]
---

class MyClass(lang.CppClass):
    template = lang.cpptype("my_namespace::MyClass< {T1}, {T2} >", "MyClass.hpp")

    def ctor(self, a: lang.AugExpr, b: lang.AugExpr) -> MyClass:
        return self.ctor_bind(a, b)

    def getA(self) -> lang.AugExpr:
        return lang.AugExpr.format("{}.getA()", self)

    def getBoth(self) -> lang.AugExpr:
        return lang.AugExpr.format("{}.getBoth()", self)

    def replace(self, a_new: lang.AugExpr, b_new: lang.AugExpr) -> lang.AugExpr:
        return lang.AugExpr.format("{}.replace({}, {})", self, a_new, b_new)
```

```{code-block} python
class MyClass(lang.CppClass):
    template = lang.cpptype("my_namespace::MyClass< {T1}, {T2} >", "MyClass.hpp")

    def getA(self) -> lang.AugExpr:
        return lang.AugExpr.format("{}.getA()", self)

    def getBoth(self) -> lang.AugExpr:
        return lang.AugExpr.format("{}.getBoth()", self)

    def replace(self, a_new: lang.AugExpr, b_new: lang.AugExpr) -> lang.AugExpr:
        return lang.AugExpr.format("{}.replace({}, {})", self, a_new, b_new)
```

Each method of `MyClass` reflects a method of the same name in its public C++ API.
These methods do not return values, but *expressions*;
here, we use the generic `AugExpr` class to model expressions that we don't know anything
about except how they should be constructed.

We create these expressions using `AugExpr.format`, which takes a format string
and interpolation arguments in the same way as `cpptype`.
Internally, it will analyze the format arguments (e.g. `self`, `a_new` and `b_new` in `replace`),
and combine information from any `AugExpr`s found among them.
These are:
 - **Variables**: If any of the input expression depend on variables, the resulting expression will
   depend on the union of all these variable sets
 - **Headers**: If any of the input expression requires certain header files to be evaluated,
   the resulting expression will require the same header files.

We can see this in action by calling one of the methods on a variable of type `MyClass`:

```{code-cell} ipython3
my_obj = MyClass(T1="int", T2="void").var("my_obj")
expr = my_obj.getBoth()
expr, lang.depends(expr), lang.includes(expr)
```

We can see: the newly created expression `my_obj.getBoth()` depends on the variable `my_obj` and
requires the header `MyClass.hpp` to be included; this header it has inherited from `my_obj`.

### Constructors

Using the `AugExpr` system, we can also model constructors of `MyClass`.
Assume `MyClass` has the constructor `MyClass(T1 a, T2 b)`.
We implement this by adding a `ctor` method to our Python interface:

```{code-block} python
class MyClass(lang.CppClass):
    ...
    
    def ctor(self, a: lang.AugExpr, b: lang.AugExpr) -> MyClass:
        return self.ctor_bind(a, b)
```

Here, we don't use `AugExpr.format`; instead, we use `ctor_bind`, which is exposed by `CppClass`.
This will generate the correct constructor invocation from the type of our `MyClass` object
and also ensure the headers required by `MyClass` are correctly attached to the resulting
expression:

```{code-cell} ipython3
a = lang.AugExpr("int").var("a")
b = lang.AugExpr("double").var("b")
expr = MyClass(T1="int", T2="double").ctor(a, b)
expr, lang.depends(expr), lang.includes(expr)
```

(field_data_structure_reflection)=
## Reflecting Field Data Structures

One key feature of pystencils-sfg is its ability to map symbolic fields
onto arbitrary array data structures
using the composer's {any}`map_field <SfgBasicComposer.map_field>` method.
The APIs of a custom field data structure can naturally be injected into pystencils-sfg
using the modelling framework described above.
However, for them to be recognized by `map_field`,
the reflection class also needs to implement the {any}`SupportsFieldExtraction` protocol.
This requires that the following three methods are implemented:

```{code-block} python
def _extract_ptr(self) -> AugExpr: ...

def _extract_size(self, coordinate: int) -> AugExpr | None: ...

def _extract_stride(self, coordinate: int) -> AugExpr | None: ...
```

The first, `_extract_ptr`, must return an expression that evaluates
to the base pointer of the field's memory buffer.
This pointer has to point at the field entry which pystencils accesses
at all-zero index and offsets (see [](#note-on-ghost-layers)).
The other two, when called with a coordinate $c \ge 0$, shall return
the size and linearization stride of the field in that direction.
If the coordinate is equal or larger than the field's dimensionality,
return `None` instead.

### Sample Field API Reflection

Consider the following class template for a field, which takes its element type
and dimensionality as template parameters
and exposes its data pointer, shape, and strides through public methods:

```{code-block} C++
template< std::floating_point ElemType, size_t DIM >
class MyField {
public:
  size_t get_shape(size_t coord);
  size_t get_stride(size_t coord);
  ElemType * data_ptr();
}
```

It could be reflected by the following class.
Note that in this case we define a custom `__init__` method in order to
intercept the template arguments `elem_type` and `dim`
and store them as instance members.
Our `__init__` then forwards all its arguments up to `CppClass.__init__`.
We then define reflection methods for `shape`, `stride` and `data` -
the implementation of the field extraction protocol then simply calls these methods.

```{code-cell} ipython3
from pystencilssfg.lang import SupportsFieldExtraction
from pystencils.types import UserTypeSpec

class MyField(lang.CppClass, SupportsFieldExtraction):
    template = lang.cpptype(
        "MyField< {ElemType}, {DIM} >",
        "MyField.hpp"
    )

    def __init__(
        self,
        elem_type: UserTypeSpec,
        dim: int,
        **kwargs,
    ) -> None:
        self._elem_type = elem_type
        self._dim = dim
        super().__init__(ElemType=elem_type, DIM=dim, **kwargs)

    #   Reflection of Public Methods
    def get_shape(self, coord: int | lang.AugExpr) -> lang.AugExpr:
        return lang.AugExpr.format("{}.get_shape({})", self, coord)
        
    def get_stride(self, coord: int | lang.AugExpr) -> lang.AugExpr:
        return lang.AugExpr.format("{}.get_stride({})", self, coord)

    def data_ptr(self) -> lang.AugExpr:
        return lang.AugExpr.format("{}.data_ptr()", self)

    #   Field Extraction Protocol that uses the above interface
    def _extract_ptr(self) -> lang.AugExpr:
        return self.data_ptr()

    def _extract_size(self, coordinate: int) -> lang.AugExpr | None:
        if coordinate > self._dim:
            return None
        else:
            return self.get_shape(coordinate)

    def _extract_stride(self, coordinate: int) -> lang.AugExpr | None:
        if coordinate > self._dim:
            return None
        else:
            return self.get_stride(coordinate)
```

Our custom field reflection is now ready to be used.
The following generator script demonstrates what code is generated when an instance of `MyField`
is passed to `sfg.map_field`:


```{code-cell} ipython3
import pystencils as ps
from pystencilssfg.lang.cpp import std

with SourceFileGenerator() as sfg:
    #   Create symbolic fields
    f = ps.fields("f: double[3D]")
    f_myfield = MyField(f.dtype, f.ndim, ref=True).var(f.name)

    #   Create the kernel
    asm = ps.Assignment(f(0), 2 * f(0))
    khandle = sfg.kernels.create(asm)

    #   Create the wrapper function
    sfg.function("invoke")(
        sfg.map_field(f, f_myfield),
        sfg.call(khandle)
    )
```

### Add a Factory Function

In the above example, an instance of `MyField` representing the field `f` is created by the
slightly verbose expression `MyField(f.dtype, f.ndim, ref=True).var(f.name)`.
Having to write this sequence every time, for every field, introduces unnecessary
cognitive load and lots of potential sources of error.
Whenever it is possible to create a field reflection using just information contained in a
pystencils {any}`Field <pystencils.field.Field>` object,
the API reflection should therefore implement a factory method `from_field`:

```{code-cell} ipython3
class MyField(lang.CppClass, SupportsFieldExtraction):
    ...

    @classmethod
    def from_field(cls, field: ps.Field, const: bool = False, ref: bool = False) -> MyField:
        return cls(f.dtype, f.ndim, const=const, ref=ref).var(f.name)

```

The above signature is idiomatic for `from_field`, and you should stick to it as far as possible.
We can now use it inside the generator script:

```{code-block} python
f = ps.fields("f: double[3D]")
f_myfield = MyField.from_field(f)
```

(note-on-ghost-layers)=
### A Note on Ghost Layers

Some care has to be taken when reflecting data structures that model the notion
of ghost layers.
Consider an array with the index space $[0, N_x) \times [0, N_y)$,
its base pointer identifying the entry $(0, 0)$.
When a pystencils kernel is generated with a shell of $k$ ghost layers
(see {any}`CreateKernelConfig.ghost_layers <pystencils.codegen.config.CreateKernelConfig.ghost_layers>`),
it will process only the subspace $[k, N_x - k) \times [k, N_x - k)$.

If your data structure is implemented such that ghost layer nodes have coordinates
$< 0$ and $\ge N_{x, y}$,
you must hence take care that
 - either, `_extract_ptr` returns a pointer identifying the array entry at `(-k, -k)`;
 - or, ensure that kernels operating on your data structure are always generated
   with `ghost_layers = 0`.

In either case, you must make sure that the number of ghost layers in your data structure
matches the expected number of ghost layers of the kernel.
