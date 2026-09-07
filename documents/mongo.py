import mimetypes
from datetime import datetime
from bson import ObjectId
import pymongo
from gridfs import GridFS
from django.conf import settings

_mongo_client = None

def get_client():
    global _mongo_client
    if _mongo_client is None:
        uri = getattr(settings, 'MONGODB_URI', 'mongodb://localhost:27017/')
        _mongo_client = pymongo.MongoClient(uri)
    return _mongo_client

def get_db():
    client = get_client()
    db_name = getattr(settings, 'MONGODB_DB_NAME', 'subject_bank_db')
    return client[db_name]

def get_fs():
    return GridFS(get_db())

def determine_category(filename, content_type):
    fn = (filename or '').lower()
    ct = (content_type or '').lower()
    
    if fn.endswith('.pdf') or 'pdf' in ct:
        return 'pdf'
    elif fn.endswith(('.ppt', '.pptx')) or 'powerpoint' in ct or 'presentation' in ct:
        return 'presentation'
    elif fn.endswith(('.doc', '.docx', '.odt', '.rtf', '.txt')) or 'word' in ct or 'document' in ct:
        return 'document'
    elif fn.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp')) or ct.startswith('image/'):
        return 'image'
    return 'other'

def format_file_size(size_bytes):
    if not size_bytes:
        return '0 B'
    if size_bytes < 1024:
        return f'{size_bytes} B'
    elif size_bytes < 1024 * 1024:
        return f'{size_bytes / 1024:.1f} KB'
    elif size_bytes < 1024 * 1024 * 1024:
        return f'{size_bytes / (1024 * 1024):.2f} MB'
    return f'{size_bytes / (1024 * 1024 * 1024):.2f} GB'

# ================= SUBJECTS & FOLDERS MANAGEMENT =================

def ensure_initial_subjects():
    db = get_db()
    subj_col = db['subjects']
    files_col = db['fs.files']
    
    # Check if any existing files have subjects not yet in subjects collection
    existing_subjects = files_col.distinct('subject')
    for subj in existing_subjects:
        if subj and not subj_col.find_one({'name': {'$regex': f'^{subj.strip()}$', '$options': 'i'}}):
            # Find folders used by this subject
            used_folders = files_col.distinct('folder', {'subject': subj})
            folders = [f for f in used_folders if f]
            if not folders:
                folders = ['General', 'Syllabus', 'Unit 1']
            subj_col.insert_one({
                'name': subj.strip(),
                'description': f'{subj} study materials, lecture slides, and notes.',
                'folders': folders,
                'created_at': datetime.utcnow()
            })

    if subj_col.count_documents({}) == 0:
        default_subjects = [
            {
                'name': 'Cloud Computing',
                'description': 'Virtualization, Cloud Architecture, AWS, Azure, and Distributed Storage.',
                'folders': ['Syllabus', 'Unit 1 - Architecture', 'Unit 2 - Virtualization', 'Assignments'],
                'created_at': datetime.utcnow()
            },
            {
                'name': 'Computer Networks',
                'description': 'OSI model, TCP/IP, routing algorithms, protocol analysis, and socket programming.',
                'folders': ['Syllabus', 'Unit 1 - Fundamentals', 'Lab Manuals', 'Question Bank'],
                'created_at': datetime.utcnow()
            },
            {
                'name': 'Operating Systems',
                'description': 'Process scheduling, concurrency, deadlocks, memory management, and file systems.',
                'folders': ['Lecture Slides', 'Assignments', 'Lab Codes'],
                'created_at': datetime.utcnow()
            },
            {
                'name': 'Mathematics',
                'description': 'Calculus, Linear Algebra, Probability, and Discrete Mathematics.',
                'folders': ['Formula Sheets', 'Tutorials', 'Previous Exam Papers'],
                'created_at': datetime.utcnow()
            }
        ]
        subj_col.insert_many(default_subjects)

def get_all_subjects_with_stats():
    ensure_initial_subjects()
    db = get_db()
    subj_col = db['subjects']
    files_col = db['fs.files']
    
    subjects = list(subj_col.find().sort('name', pymongo.ASCENDING))
    results = []
    
    for s in subjects:
        s_name = s['name']
        folders = s.get('folders', ['General'])
        
        # Count documents in this subject
        file_count = files_col.count_documents({'subject': {'$regex': f'^{s_name.strip()}$', '$options': 'i'}})
        
        # Calculate total size
        pipeline = [
            {'$match': {'subject': {'$regex': f'^{s_name.strip()}$', '$options': 'i'}}},
            {'$group': {'_id': None, 'total_size': {'$sum': '$length'}}}
        ]
        agg_res = list(files_col.aggregate(pipeline))
        total_size = agg_res[0]['total_size'] if agg_res else 0
        
        # Counts per folder
        folder_stats = []
        for f_name in folders:
            f_count = files_col.count_documents({
                'subject': {'$regex': f'^{s_name.strip()}$', '$options': 'i'},
                'folder': {'$regex': f'^{f_name.strip()}$', '$options': 'i'}
            })
            folder_stats.append({
                'name': f_name,
                'file_count': f_count
            })
            
        results.append({
            'id': str(s['_id']),
            'name': s_name,
            'description': s.get('description', ''),
            'folders': folders,
            'folder_stats': folder_stats,
            'file_count': file_count,
            'total_size': total_size,
            'total_size_formatted': format_file_size(total_size)
        })
    return results

def create_subject(name, description=""):
    name = name.strip()
    if not name:
        raise ValueError("Subject name cannot be empty")
    db = get_db()
    subj_col = db['subjects']
    if subj_col.find_one({'name': {'$regex': f'^{name}$', '$options': 'i'}}):
        raise ValueError(f"Subject '{name}' already exists.")
    
    subj_col.insert_one({
        'name': name,
        'description': description.strip() if description else f"{name} learning materials.",
        'folders': ['General', 'Unit 1', 'Syllabus'],
        'created_at': datetime.utcnow()
    })
    return True

def delete_subject(subject_name):
    db = get_db()
    subj_col = db['subjects']
    files_col = db['fs.files']
    fs = get_fs()
    
    # Delete all documents belonging to this subject
    cursor = files_col.find({'subject': {'$regex': f'^{subject_name.strip()}$', '$options': 'i'}})
    for doc in cursor:
        try:
            fs.delete(doc['_id'])
        except Exception:
            pass
            
    subj_col.delete_one({'name': {'$regex': f'^{subject_name.strip()}$', '$options': 'i'}})
    return True

def create_folder(subject_name, folder_name):
    folder_name = folder_name.strip()
    if not folder_name:
        raise ValueError("Folder name cannot be empty")
    db = get_db()
    subj_col = db['subjects']
    
    subj = subj_col.find_one({'name': {'$regex': f'^{subject_name.strip()}$', '$options': 'i'}})
    if not subj:
        raise ValueError(f"Subject '{subject_name}' not found.")
        
    folders = subj.get('folders', [])
    for existing in folders:
        if existing.lower() == folder_name.lower():
            raise ValueError(f"Folder '{folder_name}' already exists in {subject_name}.")
            
    subj_col.update_one(
        {'_id': subj['_id']},
        {'$push': {'folders': folder_name}}
    )
    return True

def delete_folder(subject_name, folder_name):
    db = get_db()
    subj_col = db['subjects']
    files_col = db['fs.files']
    fs = get_fs()
    
    subj = subj_col.find_one({'name': {'$regex': f'^{subject_name.strip()}$', '$options': 'i'}})
    if not subj:
        raise ValueError(f"Subject '{subject_name}' not found.")
        
    # Delete all files inside this folder
    cursor = files_col.find({
        'subject': {'$regex': f'^{subject_name.strip()}$', '$options': 'i'},
        'folder': {'$regex': f'^{folder_name.strip()}$', '$options': 'i'}
    })
    for doc in cursor:
        try:
            fs.delete(doc['_id'])
        except Exception:
            pass
            
    subj_col.update_one(
        {'_id': subj['_id']},
        {'$pull': {'folders': folder_name}}
    )
    return True

# ================= DOCUMENT MANAGEMENT =================

def save_document(file_obj, title, subject, folder="General", tags=None):
    fs = get_fs()
    filename = getattr(file_obj, 'name', 'untitled')
    content_type = getattr(file_obj, 'content_type', None)
    
    if not content_type or content_type == 'application/octet-stream':
        guessed_type, _ = mimetypes.guess_type(filename)
        if guessed_type:
            content_type = guessed_type
        else:
            content_type = 'application/octet-stream'

    category = determine_category(filename, content_type)
    file_bytes = file_obj.read()
    file_size = len(file_bytes)
    
    parsed_tags = []
    if tags:
        if isinstance(tags, str):
            parsed_tags = [t.strip() for t in tags.split(',') if t.strip()]
        elif isinstance(tags, list):
            parsed_tags = tags

    subject_clean = subject.strip() if subject else 'General'
    folder_clean = folder.strip() if folder else 'General'

    # Auto-add folder to subject if not present
    db = get_db()
    subj_col = db['subjects']
    subj_record = subj_col.find_one({'name': {'$regex': f'^{subject_clean}$', '$options': 'i'}})
    if subj_record:
        if folder_clean not in subj_record.get('folders', []):
            subj_col.update_one({'_id': subj_record['_id']}, {'$push': {'folders': folder_clean}})
    else:
        subj_col.insert_one({
            'name': subject_clean,
            'description': f'{subject_clean} documents and files.',
            'folders': [folder_clean],
            'created_at': datetime.utcnow()
        })

    file_id = fs.put(
        file_bytes,
        filename=filename,
        content_type=content_type,
        title=title.strip() if title else filename,
        subject=subject_clean,
        folder=folder_clean,
        tags=parsed_tags,
        category=category,
        file_size=file_size,
        upload_date=datetime.utcnow()
    )
    return str(file_id)

def get_document(file_id):
    try:
        fs = get_fs()
        oid = ObjectId(file_id)
        if fs.exists(oid):
            return fs.get(oid)
    except Exception:
        pass
    return None

def delete_document(file_id):
    try:
        fs = get_fs()
        oid = ObjectId(file_id)
        if fs.exists(oid):
            fs.delete(oid)
            return True
    except Exception:
        pass
    return False

def list_documents(query=None, subject=None, folder=None, category=None):
    db = get_db()
    files_col = db['fs.files']
    
    filter_doc = {}
    
    if subject and subject.lower() != 'all':
        filter_doc['subject'] = {'$regex': f'^{subject.strip()}$', '$options': 'i'}
        
    if folder and folder.lower() != 'all':
        filter_doc['folder'] = {'$regex': f'^{folder.strip()}$', '$options': 'i'}
        
    if category and category.lower() != 'all':
        filter_doc['category'] = category.strip().lower()
        
    if query:
        q = query.strip()
        filter_doc['$or'] = [
            {'title': {'$regex': q, '$options': 'i'}},
            {'filename': {'$regex': q, '$options': 'i'}},
            {'subject': {'$regex': q, '$options': 'i'}},
            {'folder': {'$regex': q, '$options': 'i'}},
            {'tags': {'$regex': q, '$options': 'i'}}
        ]

    cursor = files_col.find(filter_doc).sort('upload_date', pymongo.DESCENDING)
    
    results = []
    for doc in cursor:
        size = doc.get('file_size') or doc.get('length', 0)
        upload_date = doc.get('upload_date') or doc.get('uploadDate')
        formatted_date = upload_date.strftime('%b %d, %Y') if upload_date else 'Recently'
        
        results.append({
            'id': str(doc['_id']),
            'title': doc.get('title', doc.get('filename', 'Untitled')),
            'filename': doc.get('filename', 'Unknown'),
            'subject': doc.get('subject', 'General'),
            'folder': doc.get('folder', 'General'),
            'tags': doc.get('tags', []),
            'category': doc.get('category', determine_category(doc.get('filename'), doc.get('contentType'))),
            'content_type': doc.get('contentType', doc.get('content_type', 'application/octet-stream')),
            'file_size': size,
            'file_size_formatted': format_file_size(size),
            'upload_date': formatted_date,
        })
    return results

def get_stats():
    ensure_initial_subjects()
    db = get_db()
    files_col = db['fs.files']
    subj_col = db['subjects']
    
    total_docs = files_col.count_documents({})
    total_subjects = subj_col.count_documents({})
    
    pipeline = [
        {
            '$group': {
                '_id': None,
                'total_bytes': {'$sum': '$length'}
            }
        }
    ]
    agg_res = list(files_col.aggregate(pipeline))
    total_bytes = agg_res[0]['total_bytes'] if agg_res else 0
    
    return {
        'total_docs': total_docs,
        'total_subjects': total_subjects,
        'total_bytes': total_bytes,
        'total_size_formatted': format_file_size(total_bytes),
    }
