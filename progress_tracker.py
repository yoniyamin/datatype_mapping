# progress_tracker.py

scraping_progress = {"progress": 0}

def get_progress():
    """Retrieve the current scraping progress."""
    return scraping_progress

def reset_progress():
    """Reset the progress to 0."""
    scraping_progress["progress"] = 0

def update_progress(new_progress):
    """Update the progress value."""
    scraping_progress["progress"] = new_progress