import sys


def process_episode(e):
    lines = e.split('\n')[:-1]
    set_dest = lines[0].split(': ')[1]
    episode_num = int(lines[1].split(' ')[1])
    if lines[3].startswith('---'):
        actions = lines[4:]
    else:
        actions = lines[3:]
    if lines[-1].startswith('DRIVE'):
        driven_dest = lines[-1].split(' ')[1]
    else:
        driven_dest = 'NIL'
    return set_dest + "__" + driven_dest + "__" + ", ".join(actions)


def create_episode_histogram(episodes, cutoff=0.9):
    uniq_e = list(set(episodes))
    histogram = [(e, episodes.count(e)) for e in uniq_e]
    histogram.sort(key=lambda x: x[1], reverse=True)
    tot = len(episodes)
    cur_tot = 0
    for idx, x in enumerate(histogram):
        cur_tot += x[1]
        if ((float)(cur_tot / tot)) >= cutoff:
            break

    return histogram[:idx + 1]


file = sys.argv[1]
run_id = str(file.split('.')[1])
with open(file) as f:
    log_file = f.read()

episodes = [process_episode(e)
            for e in log_file.split('-------------\n')[1:-1]]
episode_histogram = create_episode_histogram(episodes)

for item in episode_histogram:
    desired, driven, episode = item[0].split("__")
    print(run_id + "\t" + str(item[1]) + "\t" +
          desired + "\t" + driven + "\t" + episode)
print()
