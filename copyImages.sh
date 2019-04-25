#!/usr/bin/env bash
# 1st argument = source folder
# 2nd argument = target folder
# copy only the files whose names matches a given list
echo "Reading and copying"
while read line
do
        cp $1/$line* $2/
done
echo "Done"
