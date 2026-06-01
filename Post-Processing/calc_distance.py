import vtk
import math

print("1. Reading lowestLayerCells...")
cell_reader = vtk.vtkGenericDataObjectReader()
cell_reader.SetFileName("VTK/lowestLayerCells_0.vtk")
cell_reader.Update()
cells = cell_reader.GetOutput()

print("2. Extracting Cell Centers...")
center_filter = vtk.vtkCellCenters()
center_filter.SetInputData(cells)
center_filter.VertexCellsOn()
center_filter.Update()
centers = center_filter.GetOutput()

print("3. Reading bedFaces...")
bed_reader = vtk.vtkGenericDataObjectReader()
bed_reader.SetFileName("VTK/bedFaces/bedFaces_0.vtk")
bed_reader.Update()
bed = bed_reader.GetOutput()

print("4. Building Spatial Locator...")
locator = vtk.vtkCellLocator()
locator.SetDataSet(bed)
locator.BuildLocator()

print("5. Calculating Distances...")
num_pts = centers.GetNumberOfPoints()
distances = vtk.vtkDoubleArray()
distances.SetName("y_Physical_Distance")
distances.SetNumberOfTuples(num_pts)

closestPoint = [0.0, 0.0, 0.0]
cellId = vtk.reference(0)
subId = vtk.reference(0)
dist2 = vtk.reference(0.0)

for i in range(num_pts):
    pt = centers.GetPoint(i)
    locator.FindClosestPoint(pt, closestPoint, cellId, subId, dist2)
    distances.SetValue(i, math.sqrt(dist2))

# Attach array to points
centers.GetPointData().AddArray(distances)

print("6. Writing Output to .vtp...")
writer = vtk.vtkXMLPolyDataWriter()
writer.SetFileName("Cell_Wall_Distances.vtp")
writer.SetInputData(centers)
writer.SetDataModeToAscii()
writer.Write()

print("SUCCESS: Distance calculation complete.")
