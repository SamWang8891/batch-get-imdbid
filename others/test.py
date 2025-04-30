# import os
#
#
# s:str = '/123/33/9ks'
#
# ss = s.split(os.sep)[-1]
#
# sss = s.replace(ss, '')
#
# print(sss)

# 等你睡醒發現我把全部都重構完了 XD
#

from RangeAdvance import RangeAdvance

flag1 = False
flag2 = False
flag3 = False
flag4 = False
flag5 = False
a = [1,2,3]
b=[4,5,6]

print(next(zip(a,b)))
c = [[1,4], [2,5], [3,6]]


print(list(zip(*(RangeAdvance(10))))[0])


for i, ctrl in RangeAdvance(10):

    while True:
        input("請輸入名稱")

        break;


    print(i)

    if i == 3 and not flag5:
        ctrl.reset(1)
        flag5 = True


    if i == 5 and not flag1:
        ctrl.stay()
        flag1 = True
        continue

    if i == 5 and not flag4:
        ctrl.stay()
        flag4 = True
        continue

    if i == 9 and not flag2:
        ctrl.stay()
        flag2 = True
        continue

    if i == 9 and not flag3:
        ctrl.stay()
        flag3 = True
