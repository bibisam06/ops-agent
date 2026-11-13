from dotenv import load_dotenv
load_dotenv()

import anthropic
client = anthropic.Anthropic()

from tools import TOOLS, TOOL_FUNCS
import json

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

        while True:  # 툴 루프: Claude가 툴을 그만 쓸 때까지 반복
            response = client.messages.create(
                model="claude-opus-5-5",
                max_tokens=4096,
                tools=TOOLS,
                messages=messages,
            )
            messages.append({"role": "assistant", "content": response.content})

            for block in response.content:
                if block.type == "text":
                    print("Claude:", block.text)

            if response.stop_reason != "tool_use":
                break  # 툴 요청 없음 → 안쪽 루프만 탈출, 다시 You: 입력으로

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  [툴 실행] {block.name}({block.input})")
                    func = TOOL_FUNCS[block.name]
                    result = func(**block.input)

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,  # 요청 id와 짝 맞추기
                        "content": json.dumps(result, ensure_ascii=False, default=str),  # 결과를 문자열로 변환
                    })

            messages.append({"role": "user", "content": tool_results})



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