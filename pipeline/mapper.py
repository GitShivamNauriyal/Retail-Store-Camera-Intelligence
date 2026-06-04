import cv2
import json
import numpy as np
import argparse

# Global state
points = []
zones = {}
current_zone_name = None
img_display = None
img_copy = None

def mouse_callback(event, x, y, flags, param):
    global points, img_display
    if event == cv2.EVENT_LBUTTONDOWN:
        points.append((x, y))
        cv2.circle(img_display, (x, y), 3, (0, 0, 255), -1)
        if len(points) > 1:
            cv2.line(img_display, points[-2], points[-1], (0, 255, 0), 2)
        cv2.imshow("Mapper", img_display)

def main():
    global img_display, img_copy, points, zones, current_zone_name
    
    parser = argparse.ArgumentParser(description="Map store zones via click.")
    parser.add_argument("--image", required=True, help="Path to store layout image")
    parser.add_argument("--output", default="zones.json", help="Output JSON file")
    args = parser.parse_args()

    img = cv2.imread(args.image)
    if img is None:
        print(f"Error: Could not load image at {args.image}")
        return

    img_copy = img.copy()
    img_display = img.copy()

    cv2.namedWindow("Mapper")
    cv2.setMouseCallback("Mapper", mouse_callback)

    print("--- Instructions ---")
    print("1. Press 'n' to start a new zone and enter its name in the terminal.")
    print("2. Left-click to add points to the current zone polygon.")
    print("3. Press 'c' to close the polygon and save the current zone.")
    print("4. Press 'r' to reset the current polygon.")
    print("5. Press 's' to save all zones to JSON and exit.")
    print("6. Press 'q' to quit without saving.")

    while True:
        cv2.imshow("Mapper", img_display)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('n'):
            current_zone_name = input("Enter zone name (e.g., PURPLLE_MUM_1076_Z01): ")
            points = []
            print(f"Started zone: {current_zone_name}. Click to add points.")
            
        elif key == ord('c'):
            if current_zone_name and len(points) > 2:
                # Close the polygon
                cv2.line(img_display, points[-1], points[0], (0, 255, 0), 2)
                zones[current_zone_name] = points.copy()
                print(f"Saved zone: {current_zone_name} with {len(points)} points.")
                current_zone_name = None
                points = []
            else:
                print("Need at least 3 points and an active zone name to close a polygon.")

        elif key == ord('r'):
            print("Resetting current polygon.")
            points = []
            img_display = img_copy.copy()
            # Redraw saved zones
            for z_name, z_pts in zones.items():
                pts_arr = np.array(z_pts, np.int32)
                pts_arr = pts_arr.reshape((-1, 1, 2))
                cv2.polylines(img_display, [pts_arr], True, (255, 0, 0), 2)

        elif key == ord('s'):
            with open(args.output, 'w') as f:
                json.dump(zones, f, indent=4)
            print(f"Saved {len(zones)} zones to {args.output}")
            break

        elif key == ord('q'):
            print("Quitting without saving.")
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
