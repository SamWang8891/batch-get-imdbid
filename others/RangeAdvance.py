
class RangeAdvance:
    """
    __ = private
    _ = protected
    nothing = public
    """

    def __init__(self, stop: int, start: int = 0, step: int = 1):
        self.__stop = stop
        self.__start = start
        self.__step = step

        # 用來追蹤當前迭代數值
        self.__current = start

        # 這些旗標用於外部呼叫時，產生不同行為
        self.__reset_flag = False
        self.__stay_flag = False
        self.__reset_value = None

        # 迭代完成後停止
        self.__finished = False

    def __iter__(self): # magic function
        # 當尚未迭代結束，就不斷進行
        while not self.__finished:
            # 若超過範圍，則結束
            if self.__current >= self.__stop:
                self.__finished = True
                break

            # 先送出目前數值
            # yield: 產生器函數，都會在此暫停，直到下一次呼叫
            yield self.__current, self

            # 如果有呼叫 reset()，就重置 __current
            if self.__reset_flag:
                self.__reset_flag = False
                # 若外部呼叫 reset(new_value)，就跳到 new_value
                # 若沒傳 new_value，則跳回原本的起點 self.__start
                self.__current = self.__reset_value if self.__reset_value is not None else self.__start

                # 直接跳到下一輪 while，不先往下加 step
                continue

            # 如果外部呼叫過 stay()，就要重複輸出同一個值
            # 可能一次呼叫多次 stay()，我們用 while 檢查
            while self.__stay_flag:
                self.__stay_flag = False
                yield self.__current, self
                # 如果外面又再呼叫一次 stay()，等回到這個 while 才會多印
                # 一樣不加 step，真正跳到下一個值要等「沒有 stay_flag」才做

            # 如果都沒有 reset 或 stay，就往下走下一個值
            self.__current += self.__step

    def reset(self, new_value=None):
        """下次迭代時，從 new_value (或起始值) 再繼續。"""
        self.__reset_flag = True
        self.__reset_value = new_value

    def stay(self):
        """下次迭代時，再多輸出一次目前值。"""
        self.__stay_flag = True
