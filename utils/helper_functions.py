

def parse_duration_to_days(duration_str):
            if not duration_str:
                return 0
            duration_str = str(duration_str).lower().strip()
            digits = ''.join(c for c in duration_str if c.isdigit() or c == '.')
            if not digits:
                return 0
            
            val = float(digits)
            if 'week' in duration_str:
                return val * 7
            elif 'month' in duration_str:
                return val * 30
            elif 'year' in duration_str:
                return val * 365
            return val  