#
# Copyright 2011 Twitter, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""
PyCascading function decorators to be used with user-defined functions.

Cascading can apply user-defined functions to tuple streams after an Each or
Every operation. These can emit a new set of tuples (using a Function after
an Each operation), keep or filter out tuples (a Filter after an Each), or
emit aggregate values (an Aggregator or Buffer for a group after an Every).

We use global Python functions to perform these user-defined operations. When
building the data processing pipeline, we can simply stream data through a
Python function with PyCascading if it was decorated by one of the decorators.
The decorator identifies the function as either a map, filter, or reduce. The
meaning of these operations is as follows:

* A 'map' function is executed for each input tuple, and returns no, one, or
several new output tuples.

* A 'filter' is a boolean-valued function, which should return true if the
input tuple should be kept for the output, and false if not.

* A 'reduce' is a function that is applied to groups of tuples, and is the
equivalent of a Cascading Buffer. It returns an aggregate after iterating
through the tuples in the group.

Exports the following:
map
filter
reduce
numargs_expected
python_list_expected
python_dict_expected
collects_output
yields
produces_python_list
produces_tuples
flowprocess_expected
"""

__author__ = 'Gabor Szabo'


from pycascading.pipe import DecoratedFunction
from com.twitter.pycascading import CascadingBaseOperationWrapper
from com.twitter.pycascading import CascadingRecordProducerWrapper


def _function_decorator(additional_parameters):
    """
    A decorator to recursively decorate a function with arbitrary attributes.
    """
    def fun_decorator(function_or_callabledict):
        if isinstance(function_or_callabledict, DecoratedFunction):
            # Another decorator is next
            dff = function_or_callabledict
        else:
            # The original function comes next
            dff = DecoratedFunction()
            dff.decorators['function'] = function_or_callabledict
            dff.decorators['type'] = 'none'
            dff.decorators['input_conversion'] = \
            CascadingBaseOperationWrapper.ConvertInputTuples.NONE
            dff.decorators['output_method'] = \
            CascadingRecordProducerWrapper.OutputMethod.YIELDS_OR_RETURNS
            dff.decorators['output_type'] = \
            CascadingRecordProducerWrapper.OutputType.AUTO
            dff.decorators['flow_process_pass_in'] = \
            CascadingRecordProducerWrapper.FlowProcessPassIn.NO
            dff.decorators['args'] = None
            dff.decorators['kwargs'] = None
        # Add the attributes to the decorated function
        dff.decorators.update(additional_parameters)
        return dff
    return fun_decorator


def numargs_expected(num):
    """The function expects a num number of fields in the input tuples.

    Arguments:
    num -- the number of fields that the input tuples must have
    """
    return _function_decorator({ 'numargs_expected' : num })


def python_list_expected():
    """PyCascading will pass in the input tuples as Python lists.

    There is some performance penalty as all the incoming tuples need to be
    converted to Python lists.
    """
    return _function_decorator({ 'input_conversion' :
    CascadingBaseOperationWrapper.ConvertInputTuples.PYTHON_LIST })


def python_dict_expected():
    """The input tuples are converted to Python dicts for this function.

    PyCascading will convert all input tuples to a Python dict for this
    function. The keys of the dict are the Cascading field names and the values
    are the values read from the tuple.

    There is some performance penalty as all the incoming tuples need to be
    converted to Python dicts.
    """
    return _function_decorator({ 'input_conversion' :
    CascadingBaseOperationWrapper.ConvertInputTuples.PYTHON_DICT })


def collects_output():
    """The function expects an output collector where output tuples are added.

    PyCascading will pass in an output collector of Cascading class
    TupleEntryCollector to which the function can add output tuples by
    calling its 'add' method.

    Use this if performance is important, as no conversion takes place between
    Python objects and Cascading tuples.
    """
    return _function_decorator({ 'output_method' : \
    CascadingRecordProducerWrapper.OutputMethod.COLLECTS })


def yields():
    """
    The function is a generator that 'yield's output tuples, in the pythonic
    sense.

    PyCascading considers this function a generator that yields one or more
    output tuples before returning. If this decorator is not used, the way the
    function emits tuples is determined automatically (which can be either
    through yielding several values or returning a single value).

    We can safely yield Nones or not yield anything at all; no output tuples
    will be emitted in this case.  
    """
    return _function_decorator({ 'output_method' : \
    CascadingRecordProducerWrapper.OutputMethod.YIELDS })


def produces_python_list():
    """The function emits Python lists as tuples.

    These will be converted by PyCascading to Cascading Tuples, so this impacts
    performance.
    """
    return _function_decorator({ 'output_type' : \
    CascadingRecordProducerWrapper.OutputType.PYTHON_LIST })


def produces_tuples():
    """The function emits native Cascading Tuples or TupleEntrys.

    No conversion takes place so this is a fast way to add tuples to the
    output.
    """
    return _function_decorator({ 'output_type' : \
    CascadingRecordProducerWrapper.OutputType.TUPLE })


def flowprocess_expected():
    """Pass in the flowProcess variable to the Python function.

    Cascading supplies a FlowProcess variable to every custom function call.
    This attribute instructs PyCascading to pass it on to the Python function.
    """
    return _function_decorator({ 'flow_process_pass_in' : \
    CascadingRecordProducerWrapper.FlowProcessPassIn.YES })


def filter():
    """This makes the function a filter.

    The function should return 'true' for each input tuple that should stay
    in the output stream, and 'false' when it needs to be filtered out.

    IMPORTANT: this behavior is the opposite of what Cascading expects!

    Note that the same effect can be attained by a map that returns the tuple
    itself or None if it should be filtered out.
    """
    return _function_decorator({ 'type' : 'filter' })


def map(produces=None):
    """The function decorated with this emits output tuples for each input one.

    The function is called for all the tuples in the input stream as happens
    in a Cascading Each. The function input tuple is passed in to the function
    as the first parameter and is a native Cascading TupleEntry unless the
    python_list_expected() or python_dict_expected() decorators are also used.

    If collects_output() is used, the 2nd parameter is a Cascading
    TupleEntryCollector to which Tuples or TupleEntrys can be added. Otherwise,
    the function may return an output tuple or yield any number of tuples if
    it is a generator.

    Whether the function yields or returns will be determined automatically if
    no decorators used that specify this, and so will be the output tuple type
    (it can be Python list or a Cascading Tuple).

    Note that the meaning of 'map' used here is closer to the Python map()
    builtin than the 'map' in MapReduce. It essentially means that each input
    tuple needs to be transformed (mapped) by a custom function.

    Arguments:
    produces -- a list of output field names
    """
    return _function_decorator({ 'type' : 'map', 'produces' : produces })


def reduce(produces=None):
    """The function decorated with reduce takes a group and emits aggregates.

    A reduce function must follow a Cascading Every operation, which comes
    after a GroupBy. The function will be called for each grouping on a
    different reducer. The first parameter passed to the function is the
    value of the grouping field for this group, and the second is an iterator
    to the tuples belonging to this group.

    Note that the iterator always points to a static variable in Cascading
    that holds a copy of the current TupleEntry, thus we cannot cache this for
    subsequent operations in the function. Instead, take iterator.getTuple() or
    create a new TupleEntry by deep copying the item in the loop.

    Cascading also doesn't automatically add the group field to the output
    tuples, so we need to do it manually. In fact a Cascading Buffer is more
    powerful than an aggregator, although it can be used as one. It acts more
    like a function emitting arbitrary tuples for groups, rather than just a
    simple aggregator.

    See http://groups.google.com/group/cascading-user/browse_thread/thread/f5e5f56f6500ed53/f55fdd6bba399dcf?lnk=gst&q=scope#f55fdd6bba399dcf
    """
    return _function_decorator({ 'type' : 'reduce', 'produces' : produces })
