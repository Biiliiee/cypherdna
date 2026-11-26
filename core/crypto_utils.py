import math

def calculate_entropy(password):
    """Calcula a entropia da senha."""
    if not password: return 0
    
    # Pool de caracteres com base no que está na senha
    pool = 0
    if any(c.islower() for c in password): pool += 26
    if any(c.isupper() for c in password): pool += 26
    if any(c.isdigit() for c in password): pool += 10
    if any(not c.isalnum() for c in password): pool += 32
    
    if pool == 0: return 0
    
    # Entropia = Tamanho * log2(Pool)
    entropy = (len(password) * math.log(pool)) / math.log(2.0)
    return round(entropy, 2)

def estimate_crack_time(entropy):
    """Retorna estimativas de tempo para quebrar a senha."""
    # 2^entropy = total combinations
    # Protege contra OverflowError quando entropia > 1024 bits (senhas muito longas)
    if entropy > 300:
        return {"rtx": "> 1000y", "pc": "> 1000y"}

    try:
        combinations = 2.0 ** entropy
    except OverflowError:
        return {"rtx": "> 1000y", "pc": "> 1000y"}
    
    rtx_4090_speed = 10**11 # hashes/sec
    common_pc_speed = 10**7  # 10 million hashes/sec
    
    def format_time(seconds):
        if seconds < 1: return "< 1 sec"
        if seconds < 60: return f"{int(seconds)}s"
        if seconds < 3600: return f"{int(seconds/60)}m"
        if seconds < 86400: return f"{int(seconds/3600)}h"
        if seconds < 31536000: return f"{int(seconds/86400)}d"
        years = int(seconds / 31536000)
        if years > 1000000:
            return "> 1000000y"
        return f"{years}y"

    return {
        "rtx": format_time(combinations / rtx_4090_speed),
        "pc": format_time(combinations / common_pc_speed)
    }

