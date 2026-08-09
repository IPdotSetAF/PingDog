  
plot_chars= "▁▂▃▅▆▇"

def plot(values, minVal, maxVal, length) -> str:
    if not values:
        return ''.join([' ']*length)
    result = [' '] * (length-len(values))
    for v in values:
        capped_v = min(max(v, minVal), maxVal)
        normalized = (capped_v - minVal) / (maxVal - minVal)
        char_index = int(normalized * (len(plot_chars) - 1))
        result.append(plot_chars[char_index])
    return ''.join(result)
