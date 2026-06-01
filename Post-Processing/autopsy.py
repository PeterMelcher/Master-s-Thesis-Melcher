import os
import sys
import re
import csv
from datetime import datetime

## This script requires the following files
#	0/alpha.water
#	0/p_rgh
#	0/U
#	0/nut
#
#	system/controlDict
#	system/fvSolution
#	system/setFieldsDict
#
#	log.interFoam
#		(logged interFoam output:					mpirun -np 8 interFoam 2>&1 | tee log.interFoam)
#	log.initSurfaceCheck
#		(logged surfaceCheck output from the initialization STL:	surfaceCheck | tee log.interFoam)
#

#1: Input Parameters
def extract_input_params(case_dir):
    inputs = {
        "maxCo": "N/A", "deltaT": "N/A", "nNonOrthogonalCorrectors": "N/A",
        "nAlphaCorr": "N/A", "nAlphaSubCycles": "N/A", "relax_p_rgh": "N/A", 
        "relax_U": "N/A", "outlet_alpha_type": "N/A", "outlet_p_rgh_type": "N/A",
        "outlet_U_type": "N/A",
        "total_setFields_boxes": 0, "river_channel_boxes": 0, 
        "inlet1_box": "N/A", "inlet2_box": "N/A",
        "init_surface_maxX": "N/A", "init_surface_thickness": "N/A",
        "flow_inlet1": "N/A", "flow_inlet2": "N/A",
        "Ks_upper_river": "N/A", "Ks_lower_river": "N/A",
        "Ks_inner_gravel": "N/A", "Ks_outer_gravel": "N/A", "Ks_vegetation": "N/A",
        "BC_U_wallsSW": "N/A", "BC_U_wallsNE": "N/A"
    }
    
    # 1.1 Control Parameters: Parse controlDict
    cd_path = os.path.join(case_dir, "system/controlDict")
    if os.path.exists(cd_path):
        with open(cd_path, "r") as f:
            content = f.read()
            m_co = re.search(r"maxCo\s+([\d\.]+);", content)
            inputs["maxCo"] = m_co.group(1) if m_co else "N/A"
            m_dt = re.search(r"^deltaT\s+([\d\.]+);", content, re.MULTILINE)
            inputs["deltaT"] = m_dt.group(1) if m_dt else "N/A"

    # 1.2 Control Parameters: Parse fvSolution
    fvs_path = os.path.join(case_dir, "system/fvSolution")
    if os.path.exists(fvs_path):
        with open(fvs_path, "r") as f:
            content = f.read()
            m_noc = re.search(r"nNonOrthogonalCorrectors\s+(\d+);", content)
            inputs["nNonOrthogonalCorrectors"] = m_noc.group(1) if m_noc else "0"
            m_ac = re.search(r"nAlphaCorr\s+(\d+);", content)
            inputs["nAlphaCorr"] = m_ac.group(1) if m_ac else "N/A"
            m_asc = re.search(r"nAlphaSubCycles\s+(\d+);", content)
            inputs["nAlphaSubCycles"] = m_asc.group(1) if m_asc else "N/A"
            
            m_rp = re.search(r"p_rgh\s+([\d\.]+);", content)
            inputs["relax_p_rgh"] = m_rp.group(1) if m_rp else "1.0"
            m_ru = re.search(r"U\s+([\d\.]+);", content)
            inputs["relax_U"] = m_ru.group(1) if m_ru else "1.0"

    # 1.3 Boundary Conditions: Parse alpha.water & p_rgh for Outlet Patch
    aw_path = os.path.join(case_dir, "0/alpha.water")
    if os.path.exists(aw_path):
        with open(aw_path, "r") as f:
            match = re.search(r"outlet\s*\{[^}]*type\s+(\w+);", f.read())
            inputs["outlet_alpha_type"] = match.group(1) if match else "N/A"
            
    pr_path = os.path.join(case_dir, "0/p_rgh")
    if os.path.exists(pr_path):
        with open(pr_path, "r") as f:
            match = re.search(r"outlet\s*\{[^}]*type\s+(\w+);", f.read())
            inputs["outlet_p_rgh_type"] = match.group(1) if match else "N/A"

    # 1.4 Boundary Conditions: Parse U for Inlets, Outlets, and Front and Back walls
    u_path = os.path.join(case_dir, "0/U")
    if os.path.exists(u_path):
        with open(u_path, "r") as f:
            content = f.read()
            m_outU = re.search(r"outlet\s*\{[^}]*type\s+(\w+);", content)
            inputs["outlet_U_type"] = m_outU.group(1) if m_outU else "N/A"
            
            m_in1 = re.search(r"inlet1\s*\{[^}]*volumetricFlowRate\s+constant\s+([\d\.]+);", content)
            inputs["flow_inlet1"] = m_in1.group(1) if m_in1 else "N/A"
            m_in2 = re.search(r"inlet2\s*\{[^}]*volumetricFlowRate\s+constant\s+([\d\.]+);", content)
            inputs["flow_inlet2"] = m_in2.group(1) if m_in2 else "N/A"
            
            m_wSW = re.search(r"wallsSW\s*\{[^}]*type\s+(\w+);", content)
            inputs["BC_U_wallsSW"] = m_wSW.group(1) if m_wSW else "N/A"
            m_wNE = re.search(r"wallsNE\s*\{[^}]*type\s+(\w+);", content)
            inputs["BC_U_wallsNE"] = m_wNE.group(1) if m_wNE else "N/A"

    # 1.5 Roughness: Parse nut
    nut_path = os.path.join(case_dir, "0/nut")
    if os.path.exists(nut_path):
        with open(nut_path, "r") as f:
            content = f.read()
            patches = ["upper_river", "lower_river", "inner_gravel", "outer_gravel", "vegetation"]
            for p in patches:
                m = re.search(fr"{p}\s*\{{[^}}]*Ks\s+uniform\s+([\d\.]+);", content)
                inputs[f"Ks_{p}"] = m.group(1) if m else "N/A"

    # 1.6 Initial Condition: Parse setFieldsDict & log.initSurfaceCheck
    sf_path = os.path.join(case_dir, "system/setFieldsDict")
    if os.path.exists(sf_path):
        with open(sf_path, "r") as f:
            content = f.read()
            
            # 1.6.1 Boxes around Inlet Patches (or Boxes in River Cannel): Parse setFieldsDict
            boxes = re.findall(r"box\s+\(([^)]+)\)\s+\(([^)]+)\);", content)
            inputs["total_setFields_boxes"] = len(boxes)
            inputs["river_channel_boxes"] = len(re.findall(r"//\s*River Channel", content, re.IGNORECASE))

            if len(boxes) >= 2:
                inputs["inlet1_box"] = f"Min({boxes[0][0]}) Max({boxes[0][1]})"
                inputs["inlet2_box"] = f"Min({boxes[1][0]}) Max({boxes[1][1]})"
                
            # 1.6.2 surfaceToCell STL: Parse log.initSurfaceCheck
            m_surf = re.search(r"surfaceToCell[\s\S]*?file\s+[\"']([^\"']+)[\"']", content)
            if m_surf:
                filename = m_surf.group(1).strip()
                # Extracts water level from file name
                # Takes string directly before .stl, converts p format into decimals (optional separators: "p", "P", ".", optional unit: "m" or "M")
                # Example: _0p05.stl, 1.5.stl, _2m.stl
                m_thick = re.search(r"_?([0-9]+(?:[pP\.][0-9]+)?)[mM]?\.[sS][tT][lL]$", filename)
                if m_thick:
                    extracted_val = m_thick.group(1).lower().replace('p', '.')
                    inputs["init_surface_thickness"] = extracted_val
                else:
                    inputs["init_surface_thickness"] = "N/A (Not in filename format)"
                
                # Extract downstream STL extension (x-dir) from surfaceCheck log
                scheck_path = os.path.join(case_dir, "log.initSurfaceCheck")
                if os.path.exists(scheck_path):
                    with open(scheck_path, "r") as slog:
                        slog_content = slog.read()
                        m_bb = re.search(r"Bounding Box\s*:\s*\([^\)]+\)\s*\(([-\.\deE]+)\s+[-\.\deE]+\s+[-\.\deE]+\)", slog_content)
                        if m_bb:
                            inputs["init_surface_maxX"] = m_bb.group(1)
                else:
                    inputs["init_surface_maxX"] = "N/A (No log)"

    return inputs

# 2: Output Parameters
def extract_output_metrics(case_dir):
    outputs = {
        "last_time": "N/A", "last_deltaT": "N/A", "max_Co": "N/A", 
        "max_alpha_Co": "N/A", "last_sum_local_cont": "N/A",
        "res_p_rgh": "N/A", "res_U": "N/A", "res_k": "N/A",
        "last_max_p": "N/A", "last_maxMag_U": "N/A"
    }
    
    log_path = os.path.join(case_dir, "log.interFoam")
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            lines = f.readlines()
            for line in reversed(lines):
                if outputs["last_time"] == "N/A" and line.startswith("Time = "):
                    outputs["last_time"] = line.split("=")[1].strip()
                elif outputs["last_deltaT"] == "N/A" and line.startswith("deltaT = "):
                    outputs["last_deltaT"] = line.split("=")[1].strip()
                elif outputs["max_Co"] == "N/A" and line.startswith("Courant Number mean:"):
                    match = re.search(r"max:\s+([\d\.\+eE\-]+)", line)
                    if match: outputs["max_Co"] = match.group(1)
                elif outputs["max_alpha_Co"] == "N/A" and line.startswith("Interface Courant Number mean:"):
                    match = re.search(r"max:\s+([\d\.\+eE\-]+)", line)
                    if match: outputs["max_alpha_Co"] = match.group(1)
                elif outputs["last_sum_local_cont"] == "N/A" and "sum local =" in line:
                    match = re.search(r"sum local = ([\d\.\+eE\-]+)", line)
                    if match: outputs["last_sum_local_cont"] = match.group(1)
                
                elif outputs["last_max_p"] == "N/A" and "max() of p_rgh =" in line:
                    match = re.search(r"max\(\) of p_rgh = ([\d\.\+eE\-]+)", line)
                    if match: outputs["last_max_p"] = match.group(1)
                elif outputs["last_maxMag_U"] == "N/A" and "maxMag() of U =" in line:
                    match = re.search(r"maxMag\(\) of U = ([\d\.\+eE\-]+)", line)
                    if match: outputs["last_maxMag_U"] = match.group(1)

                elif outputs["res_p_rgh"] == "N/A" and "Solving for p_rgh" in line:
                    match = re.search(r"Initial residual = ([\d\.\+eE\-]+)", line)
                    if match: outputs["res_p_rgh"] = match.group(1)
                elif outputs["res_U"] == "N/A" and "Solving for U" in line:
                    match = re.search(r"Initial residual = ([\d\.\+eE\-]+)", line)
                    if match: outputs["res_U"] = match.group(1)
                elif outputs["res_k"] == "N/A" and "Solving for k" in line:
                    match = re.search(r"Initial residual = ([\d\.\+eE\-]+)", line)
                    if match: outputs["res_k"] = match.group(1)
                
                if all(v != "N/A" for v in outputs.values()):
                    break
    else:
        print(f"Warning: log.interFoam not found in {case_dir}.")
        
    return outputs

def main():
    if len(sys.argv) < 2:
        print("Error: You must provide the case folder name.")
        print("Usage: python3 autopsy.py <Case_Folder_Name>")
        sys.exit(1)

    case_dir = sys.argv[1]
    if not os.path.isdir(case_dir):
        print(f"Error: Directory '{case_dir}' does not exist.")
        sys.exit(1)

    print(f"Analyzing case: {case_dir}")
    
    inputs = extract_input_params(case_dir)
    outputs = extract_output_metrics(case_dir)
    
    # Combine dictionaries for CSV
    row_data = {"Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Case_Name": case_dir}
    row_data.update(inputs)
    row_data.update(outputs)

    csv_file = "simulation_tracker.csv"
    file_exists = os.path.isfile(csv_file)
    
    try:
        with open(csv_file, mode='a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=row_data.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(row_data)
        print(f"Successfully appended data to {csv_file}")
    except PermissionError:
        print(f"Error: Could not write to {csv_file}. Is it open in Excel? Close it and try again.")

if __name__ == "__main__":
    main()
