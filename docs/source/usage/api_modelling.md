---
file_format: mystnb
kernelspec:
  name: python3
---

# Modelling C++ APIs in pystencils-sfg

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
