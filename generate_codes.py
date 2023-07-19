codes = []
cache_append = codes.append
#20*
for first in range(0, 3):
    # 20**
    for second in range(0, 4):
        # 20***
        for third in range(0, 2):
            # 20****
            for fourth in range(1, 3):
                for code1 in range(0, 10):
                    for code2 in range(0, 10):
                        for code3 in range(0, 10):
                            for code4 in range(0, 10):
                                code = f"20{first}{second}{third}{fourth}{code1}{code2}{code3}{code4}"
                                cache_append(code)

with open("codes.txt", "a") as file:
    for code in codes:
        file.write(f"{code}\n")