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
# This script is used to deploy a PyCascading job remotely to a server
#

# This is the server where the script has to be submitted
# SSH access has to be present
server=localhost
# This is the folder where a temporary directory is created for the submission
# $HOME is only expanded on the remote server
server_deploys_dir='$HOME/pycascading/deploys'
# The folder on the remote server where the master jar will be placed
server_build_dir='$HOME/pycascading'

usage()
{
	cat << EOF
Usage: $0 [options] <main_script> [additional_files]

The main_script gets executed by PyCascading. All additional_files are also
copied to the remote server and submitted together with the job to Hadoop. 

Options:
   -h           Show this message
   -b           Build PyCascading first before submitting job
   -f <file>    Copy file to the server together with main_script, but do not
   				bundle it into the Hadoop jar for submission. This option may
   				be repeated several times for multiple files. File names cannot
   				start with a dot.
   -s <server>  The name of the remote server where Hadoop is installed and the
                PyCascading jar should be deployed to

EOF
}

build_first=no
declare -a files_to_copy

while getopts ":hbf:s:" OPTION; do
	case $OPTION in
		h)	usage
         	exit 1
         	;;
        b)	build_first=yes
        	;;
        f)	files_to_copy=("${files_to_copy[@]}" "$OPTARG")
        	;;
        s)	server="$OPTARG"
        	;;
	esac
done
shift $((OPTIND-1))

main_file="$1"
if [ "$main_file" == "" -a $build_first == no ]; then
	usage
	exit 3
fi

home_dir=$(readlink -f "`dirname \"$0\"`")
tmp_dir="`mktemp -d`"

if [ $build_first == yes ]; then
	if ant -f $home_dir/java/build.xml; then
		ln -s $home_dir/build/pycascading.jar $home_dir/python/pycascading/bootstrap.py $tmp_dir
	else
		echo Build was unsuccessful, terminating.
		exit 2
	fi
fi

if [ "$main_file" != "" ]; then
	mkdir $tmp_dir/sources
	mkdir $tmp_dir/other
	for i in "$@"; do
		ln -s "`readlink -f \"$i\"`" $tmp_dir/sources
	done

	for i in "${files_to_copy[@]}"; do
		ln -s "`readlink -f \"$i\"`" $tmp_dir/other
	done
fi

# Create a setup file that will be run on the remote server
cat >$tmp_dir/setup.sh <<EOF
if [ -e pycascading.jar ]; then
	mkdir -p "$server_build_dir"
	mv pycascading.jar bootstrap.py "$server_build_dir"
fi
if [ -e sources ]; then
	mkdir -p "$server_deploys_dir"
	deploy_dir="\`mktemp -d -p \"$server_deploys_dir\"\`"
	mv run.sh sources other "\$deploy_dir"
	cd "\$deploy_dir"
	if [ -e "$server_build_dir"/pycascading.jar ]; then
		cp "$server_build_dir"/pycascading.jar deploy.jar
		cp "$server_build_dir"/bootstrap.py .
		jar uf deploy.jar -C sources .
		mv other/* sources 2>/dev/null
		rm -r other
		echo On $server run with:
		echo "   \$deploy_dir/run.sh [parameters]"
	else
		echo The PyCascading master jar has not yet been deployed, do a \"remote_deploy.sh -b\" first.
	fi
fi
EOF
chmod +x $tmp_dir/setup.sh

# Create a small script on the remote server that runs the job
cat >$tmp_dir/run.sh <<EOF
home_dir=\$(readlink -f "\`dirname \"\$0\"\`")
cd "\$home_dir/sources"
hadoop jar ../deploy.jar -Dpython.cachedir='$HOME/.jython-cache' -Dpython.cachedir.skip=0 ../bootstrap.py hadoop "$main_file" "\$@"
EOF
chmod +x $tmp_dir/run.sh

# Upload the package to the server and run the setup script
cd $tmp_dir
tar czhf - . | ssh $server "dir=\`mktemp -d\`; cd \$dir; tar xfz -; ./setup.sh; rm -r \$dir"
rm -r $tmp_dir