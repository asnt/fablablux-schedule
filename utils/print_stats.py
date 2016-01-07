import pstats

if __name__ == "__main__":
    import sys
    stats_filename = sys.argv[1]
    if len(sys.argv) > 2:
        sort_criteria = sys.argv[2]
    else:
        sort_criteria = 'cumulative'
    
    p = pstats.Stats(stats_filename)
    p.strip_dirs().sort_stats(sort_criteria).print_stats()
