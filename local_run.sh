#!/usr/bin/env bash

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

#
# Runs the PyCascading locally without Hadoop
#

if [ $# -lt 1 ]; then
	cat <<EOF
Usage: $0 <main_script.py> [parameters]

Runs the PyCascading script locally, without Hadoop.

EOF
	exit
fi

home_dir=$(dirname "$0")
source "$home_dir/java/dependencies.properties"

classpath="$home_dir/build/classes"

function add2classpath {
	for lib in $1; do
		for file in $(ls $2/$lib); do
			classpath="$classpath:$file"
		done
	done
}

# Jython jars
jython_libs='jython.jar'
add2classpath "$jython_libs" "$jython"

# Cascading jars
cascading_libs='cascading-[0-9].*.jar lib/jgrapht-*.jar'
add2classpath "$cascading_libs" "$cascading"

# Hadoop jars
hadoop_libs='hadoop-*core*.jar lib/*.jar'
add2classpath "$hadoop_libs" "$hadoop"

JYTHONPATH="$home_dir/python" java -classpath "$classpath" \
org.python.util.jython "$home_dir/python/pycascading/bootstrap.py" local "$@"