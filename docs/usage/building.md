
## Namespaces

Conceptually, there exist two different kinds of namespaces: *kernel namespaces* for the generated kernels,
and a single *code namespace* for all the generated code.
Both get mapped to standard C++ namespaces, in the end, but they fulfill different purposes in the code generator.

*Kernel namespaces* are used for grouping generated kernels together, e.g. to avoid name collisions.
If, for example, a code generation script combines kernels and functions produced by different components, each
component may create its own kernel namespace to isolate its kernels.

The *code namespace*, in contrast, envelops all the generated code. Its fully qualified name is built from two parts:

 - The *outer namespace* is defined in the [generator configuration][pystencilssfg.SfgConfiguration], typically by
   the global project configuration;
 - The *inner namespace* is defined by the code generation script, e.g. via [`SfgComposer.namespace`][pystencilssfg.SfgComposer.namespace].

These namespaces will finally occur in the generated implementation file as:

```C++
namespace outer_namespace::inner_namespace {

namespace kernels {
    /* kernel definitions */
} // namespace kernels

/* function definitions */

} // namespace outer_namespace::inner_namespace
```
