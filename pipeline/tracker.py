import sys
import json
import uuid
import datetime
import numpy as np
import redis
import torch

def check_gpu():
    print("--- GPU SAFETY CHECK ---")
    if torch.cuda.is_available():
        print(f"GPU is available. Using: {torch.cuda.get_device_name(0)}")
        return True
    else:
        print("CRITICAL WARNING: GPU is NOT available. Halting pipeline to prevent fallback to CPU.")
        sys.exit(1)

check_gpu()

from ultralytics import YOLO
import cv2

class ZoneTracker:
    def __init__(self, zones_file, redis_host='localhost', redis_port=6379, store_id="ST1076", camera_id="CAM1"):
        self.store_id = store_id
        self.camera_id = camera_id
        
        # Load zones
        try:
            with open(zones_file, 'r') as f:
                raw_zones = json.load(f)
        except FileNotFoundError:
            print(f"Warning: zones file {zones_file} not found. Continuing with empty zones.")
            raw_zones = {}
        
        self.zones = {}
        for z_name, z_points in raw_zones.items():
            self.zones[z_name] = np.array(z_points, np.int32)
            
        # Redis client
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        
        # Track state: track_id -> current_zone_name
        self.track_state = {}
        
    def get_zone_for_point(self, point):
        """Returns the zone name the point is in, or None if outside all zones."""
        for z_name, polygon in self.zones.items():
            # pointPolygonTest returns +1 if inside, 0 if on contour, -1 if outside
            if cv2.pointPolygonTest(polygon, point, False) >= 0:
                return z_name
        return None

    def emit_event(self, event_type, track_id, zone_id, hotspot):
        now = datetime.datetime.utcnow().isoformat() + "Z"
        
        # Determine zone type for mock data mapping
        zone_type = "GENERAL"
        if "BILLING" in zone_id.upper() or "QUEUE" in zone_id.upper():
            zone_type = "BILLING"
        elif "SHELF" in zone_id.upper():
            zone_type = "SHELF"
            
        event_payload = {
            "event_type": event_type,
            "track_id": int(track_id),
            "store_id": self.store_id,
            "camera_id": self.camera_id,
            "zone_id": zone_id,
            "zone_name": zone_id,  # using ID as name for simplicity if not mapped
            "zone_type": zone_type,
            "event_time": now,
            "zone_hotspot_x": float(hotspot[0]),
            "zone_hotspot_y": float(hotspot[1])
        }
        
        try:
            self.redis_client.xadd(
                "store_events_stream",
                {"event": json.dumps(event_payload)}
            )
            print(f"Emitted: {event_type} for track {track_id} in {zone_id}")
        except Exception as e:
            print(f"Failed to emit event to Redis: {e}")

    def update(self, tracks):
        """
        tracks: list of dicts with {'track_id': id, 'bbox': [x1, y1, x2, y2]}
        """
        current_frame_tracks = set()
        
        for t in tracks:
            track_id = t['track_id']
            bbox = t['bbox']
            
            current_frame_tracks.add(track_id)
            
            # Hotspot = bottom center of bounding box
            x1, y1, x2, y2 = bbox
            hotspot = ((x1 + x2) / 2, y2)
            
            current_zone = self.get_zone_for_point(hotspot)
            previous_zone = self.track_state.get(track_id)
            
            if current_zone != previous_zone:
                if previous_zone is not None:
                    # Emit exit event for previous zone
                    self.emit_event("zone_exited", track_id, previous_zone, hotspot)
                
                if current_zone is not None:
                    # Emit enter event for new zone
                    self.emit_event("zone_entered", track_id, current_zone, hotspot)
                    
                self.track_state[track_id] = current_zone

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=False, help="Path to input video, or camera index")
    parser.add_argument("--zones", default="zones.json", help="Path to zones JSON")
    parser.add_argument("--redis_host", default="localhost")
    parser.add_argument("--redis_port", type=int, default=6379)
    parser.add_argument("--show", action="store_true", help="Display tracking")
    args = parser.parse_args()

    # Load YOLO Nano model
    print("Loading YOLOv8n model...")
    model = YOLO("yolov8n.pt")
    
    tracker = ZoneTracker(
        zones_file=args.zones, 
        redis_host=args.redis_host, 
        redis_port=args.redis_port
    )

    source = args.video if args.video else 0
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"Error opening video source: {source}")
        return

    print(f"Starting processing on source {source}...")
    
    # We only care about people (class 0 in COCO)
    # device='0' enforces GPU usage
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        results = model.track(
            frame, 
            persist=True, 
            classes=[0], 
            tracker="bytetrack.yaml", 
            device='0',
            verbose=False
        )
        
        parsed_tracks = []
        if results and len(results) > 0 and results[0].boxes:
            boxes = results[0].boxes
            
            for i in range(len(boxes)):
                # YOLOv8 tracking returns ids
                if boxes.id is not None:
                    track_id = int(boxes.id[i].item())
                    # bbox format: xyxy
                    x1, y1, x2, y2 = boxes.xyxy[i].tolist()
                    
                    parsed_tracks.append({
                        'track_id': track_id,
                        'bbox': [x1, y1, x2, y2]
                    })
                    
        tracker.update(parsed_tracks)
        
        if args.show:
            annotated_frame = results[0].plot()
            
            # Draw zones
            for z_name, polygon in tracker.zones.items():
                pts_arr = polygon.reshape((-1, 1, 2))
                cv2.polylines(annotated_frame, [pts_arr], True, (0, 255, 255), 2)
                cv2.putText(annotated_frame, z_name, tuple(polygon[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                
            cv2.imshow("Tracker", annotated_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cap.release()
    cv2.destroyAllWindows()
    print("Processing complete.")

if __name__ == "__main__":
    main()
