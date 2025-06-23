from service.UnifiedProcessor import UnifiedProcessor

processor=None

def get_processor():
    global processor
    if not processor:
        processor=UnifiedProcessor()
        return processor
    return processor
