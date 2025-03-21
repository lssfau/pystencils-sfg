*****************************************
Composer API (``pystencilssfg.composer``)
*****************************************

.. module:: pystencilssfg.composer

.. autoclass:: SfgComposer
    :members:

.. autoclass:: SfgIComposer
    :members:

.. autoclass:: SfgBasicComposer
    :members:

.. autoclass:: SfgClassComposer
    :members:

.. autoclass:: SfgGpuComposer
    :members:

Custom Generators
=================

.. module:: pystencilssfg.composer.custom

.. autoclass:: CustomGenerator
    :members:


Helper Methods and Builders
===========================

.. module:: pystencilssfg.composer.basic_composer

.. autofunction:: make_sequence

.. autoclass:: KernelsAdder
    :members:

.. autoclass:: SfgFunctionSequencer
    :members:
    :inherited-members:

.. autoclass:: SfgNodeBuilder
    :members:

.. autoclass:: SfgBranchBuilder
    :members:

.. autoclass:: SfgSwitchBuilder
    :members:

.. module:: pystencilssfg.composer.class_composer

.. autoclass:: SfgMethodSequencer
    :members:
    :inherited-members:

Context and Cursor
==================

.. module:: pystencilssfg.context

.. autoclass:: SfgContext
    :members:

.. autoclass:: SfgCursor
    :members:
