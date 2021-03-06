#!/bin/bash
MVP="CADJPY240 EIG FOCUSP FTFBM100
FTFBMEMAS FTFBMMES FTFBM70 FTFBMKLCI FTFBMSCAP GHLSYS3 JMEDU 
LEBTECH LYC MPCORP MPI2 PADINI2 XINGHE YFG"
last="dgsb"

if [ $# -lt 1 ]
then
	echo "Usage: j2.sh <a2z>"
	exit 1
fi
for i in /z/data/mpv/${1}*.csv
do
	counter=`echo $i | awk -F[/.] '{print $5}'`
	if [ -n "`echo $MVP | xargs -n1 echo | grep -e \"^$counter$\"`" ]
	then
		echo "Skipped: $counter"
	else
	    invDownloadEOD.sh $counter 2011-11-11
    fi
done
