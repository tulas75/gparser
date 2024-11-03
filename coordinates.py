def normalize_coordinates(bbox, page_height, coordinate_system='bottom_left'):
    """
    Normalize coordinates to a standard coordinate system (top-left)
    Args:
        bbox (list): [x0, y0, x1, y1] coordinates
        page_height (float): Height of the page
        coordinate_system (str): Original coordinate system ('bottom_left' or 'top_left')
    Returns:
        list: Normalized coordinates [x0, y0, x1, y1]
    """
    x0, y0, x1, y1 = bbox
    
    if coordinate_system == 'bottom_left':
        # Convert from bottom-left to top-left coordinate system
        y0 = page_height - y0
        y1 = page_height - y1
        
    return [x0, y0, x1, y1]
