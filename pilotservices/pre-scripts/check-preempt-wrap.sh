#!/bin/bash

LOGFILE=/tmp/check_spot_out.log

echo "check preempt wrap sh starting" | tee --append $LOGFILE

zone=$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone)
LZ=${#zone}
region=${zone:0:$LZ-1}

iid=`curl -s http://169.254.169.254/latest/meta-data/instance-id`

isspot=$(aws ec2 describe-instances --region $region --instance-id $iid | grep -i spot)
if [ -z "$isspot" ]
then
    echo "Tis is not a spot instance, exiting" | tee --append $LOGFILE
    exit -1
else
    echo "Made sure this script is running in a spot instance" | tee --append $LOGFILE
fi

preempt_dir=$(mktemp -d)

cat <<'EOF' > ${preempt_dir}/check-preemption.sh
#!/bin/bash
LOGFILE=/tmp/check_spot_in.log
while [ 1 ]; do
    wget -q http://169.254.169.254/latest/meta-data/spot/termination-time -O /dev/null
    if [ $? -eq 0 ]
    then
        echo "termination notice is finally up, stopping condor_master" | tee --append $LOGFILE
        killall -QUIT condor_master
        exit
    fi
    echo "termination notice not up yet, sleeping 10 seconds" | tee --append $LOGFILE
    sleep 10
done
EOF

echo "Executing the inner script" | tee --append $LOGFILE
chmod +x ${preempt_dir}/check-preemption.sh
nohup ${preempt_dir}/check-preemption.sh < /dev/null >& /dev/null &
