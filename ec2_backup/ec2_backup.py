import boto3, sys, subprocess, time, json, requests, logging.config, traceback
from pytz import timezone
from botocore.client import ClientError
from datetime import datetime, timedelta, tzinfo


ec2 = None
logger =  None
exec_datetime = datetime.now().astimezone(timezone('Asia/Tokyo')).strftime('%Y-%m-%d %H:%M:%S')

exist_errors = []


def snap_tag_name_val(bk_prefix, ec2_name, volume_id):
    return "/".join([ 
                bk_prefix, 
                ec2_name, 
                volume_id
            ]) + '/'


def xfs_freeze(bk_mnt_points):
    """
    Execute `xfs_freeze -f`.
    """
    for mnt_point in bk_mnt_points:
        subprocess.check_call('xfs_freeze -f {} && sleep 1'.format(mnt_point), shell=True)


def xfs_unfreeze(bk_mnt_points):
    """
    Execute `xfs_freeze -u`.
    """
    for mnt_point in bk_mnt_points:
        try:
            subprocess.check_call('sleep 1 && xfs_freeze -u {} > /dev/null 2>&1'.format(mnt_point), shell=True)
        except Exception as e:
            exist_errors.append("Backup Error: {}".format(e))
            exist_errors.append(traceback.format_exc())
    

def create_snapshots(inst_desc, bk_prefix, bk_mnt_points):
    """
    Create ebs snapshot, before xfs_freeze -f, after xfs_freeze -u.
    Args:
         inst_desc: ec2 instance description. 
         bk_prefix: name of snapshot tag prefix.
         bk_mnt_points: backup mount point list.
    Returns:
         None
    """

    descriptions = {}
    tags = {t['Key']: t['Value'] for t in inst_desc['Tags']}
    ec2_name = tags['Name']

    assert ec2_name, "ec2_name is Empty"


    xfs_freeze(bk_mnt_points)

    take_snap_list = []

    for b in inst_desc['BlockDeviceMappings']:

        if b.get('Ebs') is None:
            continue

        volume_id = b['Ebs']['VolumeId']

        description = snap_tag_name_val(bk_prefix, ec2_name, volume_id)

        snap = ec2.create_snapshot(VolumeId = volume_id)

        ec2.create_tags(
                Resources=[snap['SnapshotId']],
                Tags=[{ 'Key': 'Name', 'Value': description}, { 'Key': 'backup_date', 'Value': exec_datetime }]
               )

        take_snap_list.append((snap['SnapshotId'], description))

    xfs_unfreeze(bk_mnt_points)

    for snap_id, desc in take_snap_list:
        logger.info('Create snapshot: {}({}/{})'.format(snap_id, desc, exec_datetime))


def delete_old_snapshots(inst_desc, retention, bk_prefix):
    """
    Delete ebs snapshot.
    Args:
         inst_desc: ec2 instance description. 
         retention: backup retention count.
         bk_prefix: name of snapshot tag prefix.
    Returns:
         None
    """
    ec2_tags = {t['Key']: t['Value'] for t in inst_desc['Tags']}
    ec2_name = ec2_tags.get('Name', "")

    assert ec2_name, "ec2_name is Empty"

    for b in inst_desc['BlockDeviceMappings']:
        if b.get('Ebs') is None:
            continue

        volume_id = b['Ebs']['VolumeId']
        attach_snaps = ec2.describe_snapshots(Filters=[{'Name':'volume-id','Values':[volume_id]}])

        attach_snaps_del = []

        for snap in attach_snaps['Snapshots']:

            if not 'Tags' in snap:
                continue

            snap_tags = {kv['Key']: kv['Value'] for kv in snap.get('Tags', None)}

            if snap_tags['Name'] == snap_tag_name_val(bk_prefix, ec2_name, volume_id):

                # Add '(snapshotId, snapshot datetime, snapshot Name of tag)' as tuple.
                snap_datetime = datetime.strptime(snap_tags['backup_date'], '%Y-%m-%d %H:%M:%S')
                attach_snaps_del.append((snap['SnapshotId'], snap_datetime, snap_tags['Name']))

        # Delete snapshot on the basis of retention.
        # Sort by snapshot datetime.
        sorted_exist_snap = sorted(attach_snaps_del, key=lambda sort_snap: sort_snap[1], reverse = True)

        for del_snap in sorted_exist_snap[retention:]:
            ec2.delete_snapshot(SnapshotId = del_snap[0])
            logger.info('Delete snapshot: {}({}/{})'.format(del_snap[0], del_snap[2], del_snap[1]))


def read_config(config_json):
    """
    Read backup config.
    Args:
        config_json: `config.json` file path.
    Returns:
        json object of config.json
    """

    with open(config_json, 'r') as f:
        cj = json.load(f)

    return cj['Region'], cj['Retention'], cj['Backup_prefix'], \
             [mnt_point.strip() for mnt_point in cj['Backup_mount_points']]


if __name__ == '__main__':

    argvs = sys.argv
    bk_mnt_points = None

    try:
        logging.config.fileConfig("logging.conf")
        logger = logging.getLogger()
        logger.info('[Start ec2 backup]')

        region, retention, bk_prefix, bk_mnt_points  = read_config(argvs[1])

        ec2 = boto3.client('ec2', region_name = region)
        inst_id = requests.get('http://169.254.169.254/latest/meta-data/instance-id').text

        assert inst_id, "EC2 InstanceId is Empty"

        inst_desc = ec2.describe_instances(
                        Filters=[{'Name':'instance-id', 'Values':[inst_id]}]
                    )['Reservations'][0]['Instances'][0]

        ### Create Snapshot.
        create_snapshots(inst_desc, bk_prefix, bk_mnt_points)

        ### Delete Old Snapshot.
        delete_old_snapshots(inst_desc, retention, bk_prefix)

    except Exception as e:
        exist_errors.append("Backup Error: {}".format(e))
        exist_errors.append(traceback.format_exc())

    finally:

        if exist_errors:
            xfs_unfreeze(bk_mnt_points)
            logger.info('\n'.join(exist_errors))

        logger.info('[End ec2 backup]\n')
