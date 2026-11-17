from dotenv import load_dotenv
load_dotenv()

import anthropic
client = anthropic.Anthropic()

from agent.tools import TOOLS, TOOL_FUNCS
import json

SYSTEM_PROMPT = """
너는 Docker 컨테이너 환경의 장애를 진단하는 운영(SRE) 에이전트다.
사용자의 질문에 추측하지 말고, 반드시 툴로 확인한 근거를 바탕으로 답한다.

## 환경
- 컨테이너: api-server(진단 대상 FastAPI), prometheus, cadvisor
- Prometheus 주요 메트릭
  - 요청 수: http_requests_total{method, path, status}
  - CPU: rate(container_cpu_usage_seconds_total{name="api-server"}[1m])
  - 메모리: container_memory_usage_bytes{name="api-server"}

## 진단 절차
1. get_container_list로 컨테이너 상태부터 확인한다 (죽었거나 재시작 중인지).
2. get_container_stats / query_prometheus로 CPU·메모리·에러율 이상을 찾는다.
   - 에러율: sum(rate(http_requests_total{status=~"5.."}[1m])) by (path)
3. 이상이 보이면 get_container_logs로 원인(예외, 스택트레이스)을 확인한다.
4. 근거가 부족하면 툴을 더 호출하고, 그래도 모르면 모른다고 말한다.

## 답변 형식
진단 결과는 항상 아래 형식으로 끝낸다.
- 장애 유형: cpu_spike | memory_leak | error_spike | none
- 원인 컨테이너: <이름>
- 근거: <확인한 수치/로그 1~3줄>
- 권장 조치: <1~2줄>
"""

MAX_TURNS = 10

def chat(messages : list) -> str:
    for turn in range(MAX_TURNS):
        # ① Claude 호출
        response = client.messages.create(
            model="claude-opus-5-5",
            max_tokens=4096,
            tools=TOOLS,
            messages=messages,
            system=SYSTEM_PROMPT,
        )

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            return "".join(b.text for b in response.content if b.type == "text")


        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"  [툴 실행] {block.name}({block.input})")
                try:
                    func = TOOL_FUNCS[block.name]  # 없는 툴 이름이면 KeyError → except로
                    result = func(**block.input)
                    content, is_error = json.dumps(result, ensure_ascii=False, default=str), False
                except Exception as e:
                    # 실패도 결과로 돌려줘서 Claude가 보고 다시 시도하게 함
                    content, is_error = f"{type(e).__name__}: {e}", True
                    print(f"  [툴 에러] {content}")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,  # 요청 id와 짝 맞추기
                    "content": content,
                    "is_error": is_error,
                })

        messages.append({"role": "user", "content": tool_results})

    msg = f"툴 호출이 {MAX_TURNS}회를 넘어 중단했어요."
    messages.append({"role": "assistant", "content": msg})
    return msg


def run():
    messages = []

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):  # Ctrl+C, Ctrl+D
            print("\nbye🥹")
            break

        if user_input.lower() in ("exit", "quit"):
            break
        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})
        answer = chat(messages)

        print("Claude:", answer)



def run_test(question: str = "지금 실행 중인 컨테이너 뭐 있어?"):
    """질문 하나를 보내고 response 구조를 그대로 출력해서 확인하는 테스트용 함수."""
    response = client.messages.create(
        model="claude-opus-5-5",
        max_tokens=1024,
        tools=TOOLS,
        messages=[{"role": "user", "content": question}],
    )

    # 1. 전체 구조 (JSON 형태로 보기 좋게)
    print("===== 전체 response =====")
    print(response.model_dump_json(indent=2))

    # 2. 핵심 필드만
    print("\n===== 핵심 필드 =====")
    print("stop_reason:", response.stop_reason)
    print("usage:", response.usage.input_tokens, "in /", response.usage.output_tokens, "out")

    # 3. content 블록 하나씩
    print("\n===== content 블록 =====")
    for i, block in enumerate(response.content):
        print(f"[{i}] type={block.type}")
        if block.type == "text":
            print("    text:", block.text)
        elif block.type == "tool_use":
            print("    id:", block.id)
            print("    name:", block.name)
            print("    input:", block.input)

    return response


if __name__ == "__main__":
    run()