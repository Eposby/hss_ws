string target_type
string target_color
float32 confidence
int32 pixel_x
int32 pixel_y
int32 bbox_width
int32 bbox_height
int32 bbox_x_min
int32 bbox_y_min
int32 bbox_x_max
int32 bbox_y_max
int32 aim_x
int32 aim_y
int32 error_x
int32 error_y
bool is_tracked
bool is_friendly
bool has_balloon
int32 target_id

# Target Range Estimation 
float32 estimated_range_m

# Friend/Foe info
string vehicle_color

# Balloon specific bbox
int32 balloon_cx
int32 balloon_cy
int32 balloon_bbox_x_min
int32 balloon_bbox_y_min
int32 balloon_bbox_x_max
int32 balloon_bbox_y_max
bool balloon_detected
