#!/bin/bash

if [ 1 = 1 ];
then
    preempt_dir=$(mktemp -d)

    cat <<'EOF' > ${preempt_dir}/check-preemption.sh
#!/bin/bash

while [ 1 ]; do
    wget -q http://169.254.169.254/latest/meta-data/spot/termination-time -O /dev/null
    if [ $? -eq 0 ]
    then
        killall -QUIT condor_master
        exit
    fi
    sleep 10
done
EOF

chmod +x ${preempt_dir}/check-preemption.sh
nohup ${preempt_dir}/check-preemption.sh < /dev/null >& /dev/null &
fi
