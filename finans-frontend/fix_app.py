with open("app.py", "r") as f:
    lines = f.readlines()

for i in range(len(lines)):
    # 1102, 1112, 1120, 1166 need to use df_plot
    if i in [1101, 1111, 1119, 1165]: # 0-indexed
        lines[i] = lines[i].replace("df_hist['record_date']", "df_plot['record_date']")

with open("app.py", "w") as f:
    f.writelines(lines)
