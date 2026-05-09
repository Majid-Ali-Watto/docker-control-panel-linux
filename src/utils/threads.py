import threading

def startThreadForTask(task):
    """Start a thread for a given task"""
    return threading.Thread(target=task, daemon=True).start()
    
