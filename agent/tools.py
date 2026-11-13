import docker, httpx

TOOLS = [
    {
        "name": "get_container_list",
        "description": "실행 중인 Docker 컨테이너 목록을 조회한다.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name" : "get_container_stats",
        "description" : "특정 컨테이너의 현재 CPU/메모리 사용량을 조회한다. 컨테이너 이름은 get_container_list로 먼저 확인할 수 있다.",
        "input_schema" : {"type" : "object", "properties" : {
            "name" : {"type" : "string", "description" : "컨테이너 이름 또는 ID"}
        },
        "required" : ["name"],
        },
    },
]

## tools ##

def get_container_list():
    client = docker.from_env()
    containers = client.containers.list()

    result = [
        {"name": c.name, "status": c.status, "image": c.image.tags}
        for c in containers
    ]
    print(result)
    return result


def get_container_stats(name : str):
    client = docker.from_env()
    container = client.containers.get(name)
    s = container.stats(stream=False)

    # CPU % 계산
    cpu_delta = s["cpu_stats"]["cpu_usage"]["total_usage"] - s["precpu_stats"]["cpu_usage"]["total_usage"]
    sys_delta = s["cpu_stats"]["system_cpu_usage"] - s["precpu_stats"].get("system_cpu_usage", 0)
    cpus = s["cpu_stats"].get("online_cpus", 1)
    cpu_pct = (cpu_delta / sys_delta) * cpus * 100 if sys_delta > 0 else 0.0

    # 메모리
    mem_used = s["memory_stats"]["usage"]
    mem_limit = s["memory_stats"]["limit"]
    return {
        "name": container.name,
        "cpu_percent": round(cpu_pct, 2),
        "mem_used_mb": round(mem_used / 1024 ** 2, 1),
        "mem_limit_mb": round(mem_limit / 1024 ** 2, 1),
        "mem_percent": round(mem_used / mem_limit * 100, 2),
    }



TOOL_FUNCS = {
    "get_container_list": get_container_list,
    "get_container_stats": get_container_stats,
}



