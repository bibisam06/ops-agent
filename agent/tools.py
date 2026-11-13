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
    {
        "name" : "get_container_logs",
        "description" : "특정 컨테이너의 로그를 조회한다. 컨테이너 이름은 get_container_list로 먼저 확인할 수 있다.",
        "input_schema" : {"type" : "object", "properties" : {
            "name" : {"type" : "string", "description" : "컨테이너 이름 또는 ID"},
            "tail" : {"type" : "integer", "description" : "최근 몇 줄의 로그를 조회할지 설정한다. 기본값은 50이다.", "default" : 50}
        },
        "required" : ["name"]
        },
    },
    {
        "name": "query_prometheus",
        "description": "Prometheus에 PromQL 쿼리를 실행해 결과를 조회한다. "
                       "사용 가능한 메트릭: http_requests_total (라벨: method, path, status), "
                       "cAdvisor의 container_cpu_usage_seconds_total, container_memory_usage_bytes 등 "
                       "(라벨 name으로 컨테이너 지정). 요청률은 rate(...[1m]) 형태로 조회한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "실행할 PromQL 쿼리"}
            },
            "required": ["query"],
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

def get_container_logs(name : str, tail : int = 50):
    client = docker.from_env()
    container = client.containers.get(name)
    logs = container.logs(tail=tail)
    return logs.decode("utf-8", errors="replace")


'''
r = httpx.get("http://localhost:9090/api/v1/query",
              params={"query": "http_requests_total"})
print(r.json()["data"]["result"])

'''

#http://localhost:9090/api/v1/query
def query_prometheus(query : str):
    response = httpx.get("http://localhost:9090/api/v1/query", params={"query": query}, timeout=10)
    return (
        response.json()["data"]["result"]
        if response.status_code == 200
        else {"error": response.json()["error"]}
    )

TOOL_FUNCS = {
    "get_container_list": get_container_list,
    "get_container_stats": get_container_stats,
    "get_container_logs": get_container_logs,
    "query_prometheus": query_prometheus,
}


if __name__ == "__main__":
    print("HELLO")
