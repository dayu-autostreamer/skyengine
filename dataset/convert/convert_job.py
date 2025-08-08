import yaml

# 输入文件名
input_file_path = r'./agv-instances/brandimarte/mk01.txt'
# 输出文件名
output_file_path = 'job_config.yaml'

# 读取文件
with open(input_file_path, 'r') as file:
    lines = file.readlines()


# 第一行：job 数量和 machine 数量（我们主要用 job 数量）
n_jobs, n_machines = map(int, lines[0].split())

jobs = []

for job_id in range(n_jobs):
    nums = list(map(int, lines[1 + job_id].split()))
    
    # 第一个数字：该 job 的 operation 数量
    num_operations = nums[0]
    index = 1  # 当前读取位置
    operations = []
    
    for op_id in range(num_operations):
        # 该 operation 的可选机器数量
        num_machines_for_op = nums[index]
        index += 1
        
        machines = []
        for _ in range(num_machines_for_op):
            machine_id = nums[index]
            time = nums[index + 1]
            index += 2
            machines.append({'id': machine_id, 'time': time})
        
        operations.append({
            'operation': {
                'id': op_id,
                'machines': machines
            }
        })
    
    jobs.append({
        'job': {
            'id': job_id,
            'operations': operations
        }
    })

# 构建最终 YAML 结构
config = {
    'config': {
        'jobs': jobs
    }
}

with open(output_file_path, 'w') as f:
    yaml.dump(config, f, default_flow_style=False, sort_keys=False, indent=2)