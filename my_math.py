from scipy import stats

class Math:
    @staticmethod
    def mode(arr):
        # Trả về giá trị xuất hiện nhiều nhất theo định dạng array/list
        # để code gốc gọi tới y_leter_mode[0] có thể chạy được.
        mode_result = stats.mode(arr, keepdims=False)
        return [int(mode_result.mode)]
