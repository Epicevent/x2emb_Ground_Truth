import re

# 숫자+조 뒤에 선택적으로 '의+숫자'가 붙을 수 있는 형태
section_pattern = re.compile(r"^제(\d+조(?:의\d+)?)\((.*?)\)")

test_lines = [
    "제6조(어쩌구)",
    "제6조의2(보안과제)",
    "제123조(테스트)",
    "제123조의45(아주 특별한 케이스)",
    "제12조()  사실상 내용이 없는 경우",
    "제6조의2의3(복잡해질 수도)"
]

for line in test_lines:
    match = section_pattern.match(line)
    if match:
        print(f"[매칭 성공] line='{line}'")
        print(f"  group(1)={match.group(1)}  # '6조', '6조의2', '123조의45' 등")
        print(f"  group(2)={match.group(2)}  # 괄호 안 내용")
    else:
        print(f"[매칭 실패] line='{line}'")
re.ㅁ