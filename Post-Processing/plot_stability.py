import os
import sys
import re
import matplotlib.pyplot as plt

# --- LaTeX Readability Font Configuration ---
plt.rcParams.update({
    'font.size': 14,             # Base font size
    'axes.labelsize': 16,        # X/Y axis label font size
    'axes.titlesize': 16,        # Subplot title font size
    'xtick.labelsize': 14,       # X-axis tick font size
    'ytick.labelsize': 14,       # Y-axis tick font size
    'legend.fontsize': 13,       # Legend font size
    'figure.titlesize': 18,      # Main figure Suptitle font size
    'lines.linewidth': 2.0       # Thicker lines so they don't vanish on paper
})
# --------------------------------------------

## This script requires a logged file of the interFoam output
#       (command:       mpirun -np 8 interFoam -parallel 2>&1 | tee log.interFoam)
#

def plot_log(case_dir, requested_plots, t_min=None, t_max=None, pre_crash_threshold=None):
    log_path = os.path.join(case_dir, "log.interFoam")
    if not os.path.exists(log_path):
        print(f"Error: {log_path} not found.")
        return
        
    data = {}
    current_time = None

    # Parse log
    with open(log_path, 'r') as f:
        for line in f:
            if line.startswith("Time = "):
                current_time = float(line.split("=")[1].strip())
                if current_time not in data:
                    data[current_time] = {}
            elif current_time is not None:
                if line.startswith("deltaT = "):
                    data[current_time]['deltaT'] = float(line.split("=")[1].strip())
                elif line.startswith("Courant Number mean:"):
                    m = re.search(r"max:\s+([\d\.\+eE\-]+)", line)
                    if m: data[current_time]['maxCo'] = float(m.group(1))
                elif line.startswith("Interface Courant Number mean:"):
                    m = re.search(r"max:\s+([\d\.\+eE\-]+)", line)
                    if m: data[current_time]['maxAlphaCo'] = float(m.group(1))
                elif "sum local =" in line:
                    m = re.search(r"sum local = ([\d\.\+eE\-]+)", line)
                    if m: data[current_time]['cont_err'] = float(m.group(1))
                elif "max() of p_rgh =" in line:
                    m = re.search(r"max\(\) of p_rgh = ([\d\.\+eE\-]+)", line)
                    if m: data[current_time]['max_p'] = float(m.group(1))
                elif "maxMag() of U =" in line:
                    m = re.search(r"maxMag\(\) of U = ([\d\.\+eE\-]+)", line)
                    if m: data[current_time]['maxMag_U'] = float(m.group(1))

    times = sorted(data.keys())
    valid_times = [t for t in times if 'deltaT' in data[t] and 'maxCo' in data[t]]
    
    # PreCrash Threshold
    if pre_crash_threshold is not None:
        if t_min is None:
            t_min = 0.0002 
            
        previous_t = None
        for t in valid_times:
            u_mag = data[t].get('maxMag_U', 0)
            if u_mag >= pre_crash_threshold:
                t_max = previous_t if previous_t is not None else t
                break
            previous_t = t

    # Time Window Filters (Global X-Axis)
    if t_min is not None:
        valid_times = [t for t in valid_times if t >= t_min]
    if t_max is not None:
        valid_times = [t for t in valid_times if t <= t_max]

    if not valid_times:
        print("Error: No valid time steps found within the specified time range.")
        return

    # Valid plot categories
    plot_map = {
        'deltat': {'y': [data[t].get('deltaT', 0) for t in valid_times], 'label': 'deltaT', 'color': 'b-', 'log': True, 'ylabel': 'deltaT [s]'},
        'co': {'y1': [data[t].get('maxCo', 0) for t in valid_times], 'y2': [data[t].get('maxAlphaCo', 0) for t in valid_times], 'label1': 'maxCo', 'label2': 'maxAlphaCo', 'c1': 'r-', 'c2': 'g--', 'log': False, 'ylabel': 'Courant Number'},
        'continuity': {'y': [data[t].get('cont_err', 1e-15) for t in valid_times], 'label': 'Sum Local Continuity', 'color': 'k-', 'log': True, 'ylabel': 'Continuity Error'},
        'velocity': {'y': [data[t].get('maxMag_U', 0) for t in valid_times], 'label': 'max u_mag', 'color': 'r-', 'log': False, 'ylabel': 'Flow Velocity [m/s]'},
        'pressure': {'y': [data[t].get('max_p', 0) for t in valid_times], 'label': 'max(p_rgh)', 'color': 'c-', 'log': False, 'ylabel': 'Pressure [Pa]'}
    }

    if not requested_plots:
        requested_plots = [{'name': p, 'ymin': None, 'ymax': None, 'legend_loc': 'upper right'} for p in ['deltat', 'co', 'continuity', 'velocity', 'pressure']]
    else:
        requested_plots = [p for p in requested_plots if p['name'] in plot_map]

    num_plots = len(requested_plots)
    if num_plots == 0:
        print("Error: No valid plots requested. Options: deltat, co, continuity, velocity, pressure")
        return

    # Increased default height slightly to accommodate larger fonts without overlapping
    fig, axs = plt.subplots(num_plots, 1, figsize=(10, 4.0 * num_plots), sharex=True)
    if num_plots == 1: axs = [axs]

    for i, p_config in enumerate(requested_plots):
        ax = axs[i]
        p_name = p_config['name']
        p_data = plot_map[p_name]
        
        if p_name == 'co':
            ax.plot(valid_times, p_data['y1'], p_data['c1'], label=p_data['label1'])
            ax.plot(valid_times, p_data['y2'], p_data['c2'], label=p_data['label2'])
        else:
            ax.plot(valid_times, p_data['y'], p_data['color'], label=p_data['label'])
            
        if p_data['log']:
            ax.set_yscale('log')
        else:
            ax.ticklabel_format(axis='y', style='plain', useOffset=False)
            
        # Apply local Y-Axis limits if specified
        if p_config['ymin'] is not None:
            ax.set_ylim(bottom=p_config['ymin'])
        if p_config['ymax'] is not None:
            ax.set_ylim(top=p_config['ymax'])
           
        ax.set_ylabel(p_data['ylabel'], fontweight='bold')
        ax.legend(loc=p_config['legend_loc'])
        ax.grid(True, linestyle='--', alpha=0.7)
        
        if i == num_plots - 1:
            ax.set_xlabel('Time [s]', fontweight='bold')

    case_name = os.path.basename(os.path.normpath(case_dir))
    title = f"Simulation Analysis: {case_name}"
    if t_min is not None or t_max is not None:
        title += f" (t={t_min if t_min else 0} to {t_max if t_max else 'end'})"
    plt.suptitle(title, fontweight='bold')
    
    # Pad tighter layout so larger fonts don't clip at the edges
    plt.tight_layout(pad=2.0)
    
    os.makedirs("_plots", exist_ok=True)
    
    plot_names = [p['name'] for p in requested_plots]
    suffix = "_" + "_".join(plot_names) if len(plot_names) < 5 else "_all"
    if t_min is not None or t_max is not None:
        suffix += f"_t{t_min if t_min else 0}to{t_max if t_max else 'end'}"
        
    out_file = os.path.join("_plots", f"{case_name}{suffix}.png")
    
    plt.savefig(out_file, dpi=300, bbox_inches='tight')
    print(f"Plot saved as {out_file}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 plot_health.py <case_folder> [plots...] [--min VAL] [--max VAL] [--ul|--ur|--ll|--lr] [--tmin VAL] [--tmax VAL]")
        print("Options: deltat, co, continuity, velocity, pressure")
        sys.exit(1)
        
    args = sys.argv[1:]
    case_dir = args.pop(0)
    
    t_min = None
    t_max = None
    pre_crash_threshold = None
    requested_plots = [] # Stores dictionaries like {'name': 'velocity', 'ymin': 0, 'ymax': 100, 'legend_loc': 'upper right'}
    
    # Sequential argument parser
    i = 0
    while i < len(args):
        arg = args[i].lower()
        
        if arg == '--precrash':
            if i + 1 < len(args) and args[i+1].replace('.', '', 1).isdigit():
                pre_crash_threshold = float(args[i+1])
                i += 2
            else:
                pre_crash_threshold = 500.0
                i += 1
        elif arg == '--tmin':
            t_min = float(args[i+1])
            i += 2
        elif arg == '--tmax':
            t_max = float(args[i+1])
            i += 2
        elif arg in ['deltat', 'co', 'continuity', 'velocity', 'pressure']:
            # Create a new plot config block, defaulting to upper right
            requested_plots.append({'name': arg, 'ymin': None, 'ymax': None, 'legend_loc': 'upper right'})
            i += 1
        elif arg == '--min':
            if requested_plots:
                requested_plots[-1]['ymin'] = float(args[i+1])
            else:
                print("Warning: --min ignored. You must specify a plot parameter (e.g., 'velocity') before --min.")
            i += 2
        elif arg == '--max':
            if requested_plots:
                requested_plots[-1]['ymax'] = float(args[i+1])
            else:
                print("Warning: --max ignored. You must specify a plot parameter (e.g., 'velocity') before --max.")
            i += 2
        elif arg in ['--ul', '--ur', '--ll', '--lr']:
            if requested_plots:
                loc_map = {'--ul': 'upper left', '--ur': 'upper right', '--ll': 'lower left', '--lr': 'lower right'}
                requested_plots[-1]['legend_loc'] = loc_map[arg]
            else:
                print(f"Warning: {arg} ignored. You must specify a plot parameter before setting legend location.")
            i += 1
        else:
            print(f"Warning: Unknown argument '{args[i]}' ignored.")
            i += 1
            
    plot_log(case_dir, requested_plots, t_min, t_max, pre_crash_threshold)
