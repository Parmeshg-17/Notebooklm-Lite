import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus } from 'lucide-react';
import Modal from '../common/Modal';
import Button from '../common/Button';
import { useUIStore, useNotebookStore } from '../../store';

const TAGS = ['Machine Learning', 'Infrastructure', 'Strategy', 'Genomics', 'Systems', 'Security', 'Finance', 'Research', 'General'];

export default function CreateNotebookModal() {
  const { closeCreateNotebookModal } = useUIStore();
  const { createNotebook, setActiveNotebook } = useNotebookStore();
  const navigate = useNavigate();

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [tag, setTag] = useState('General');
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = () => {
    const errs: Record<string, string> = {};
    if (!title.trim()) errs.title = 'Title is required';
    if (title.length > 100) errs.title = 'Title must be under 100 characters';
    return errs;
  };

  const handleSubmit = async () => {
    const errs = validate();
    if (Object.keys(errs).length > 0) { setErrors(errs); return; }

    try {
      const nb = await createNotebook({ title: title.trim(), description: description.trim(), tag });
      setActiveNotebook(nb.id);
      closeCreateNotebookModal();
      navigate(`/workspace/${nb.id}`);
    } catch {
      const id = `nb-${Date.now()}`;
      setActiveNotebook(id);
      closeCreateNotebookModal();
      navigate(`/workspace/${id}`);
    }
  };

  const inputStyle = {
    backgroundColor: 'var(--color-surface-container-low)',
    border: '1px solid var(--color-outline-variant)',
    color: 'var(--color-on-surface)',
    borderRadius: '0.5rem',
    outline: 'none',
    width: '100%',
    padding: '0.5rem 0.75rem',
    fontSize: '0.8125rem',
    lineHeight: '1.25rem',
    fontFamily: 'inherit',
  };

  return (
    <Modal
      title="Create New Notebook"
      onClose={closeCreateNotebookModal}
      footer={
        <>
          <Button variant="secondary" onClick={closeCreateNotebookModal}>Cancel</Button>
          <Button variant="primary" icon={<Plus size={16} />} onClick={handleSubmit}>
            Create Notebook
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <div>
          <label className="block text-label-md mb-1.5" style={{ color: 'var(--color-on-surface)' }}>
            Notebook Title <span style={{ color: 'var(--color-error)' }}>*</span>
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => { setTitle(e.target.value); setErrors((p) => ({ ...p, title: '' })); }}
            placeholder="e.g., LLM Inference Optimization"
            style={{
              ...inputStyle,
              borderColor: errors.title ? 'var(--color-error)' : 'var(--color-outline-variant)',
            }}
          />
          {errors.title && (
            <p className="text-label-sm mt-1" style={{ color: 'var(--color-error)' }}>{errors.title}</p>
          )}
        </div>

        <div>
          <label className="block text-label-md mb-1.5" style={{ color: 'var(--color-on-surface)' }}>
            Description
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Briefly describe the research focus or purpose of this notebook..."
            rows={3}
            style={{ ...inputStyle, resize: 'vertical' }}
          />
        </div>

        <div>
          <label className="block text-label-md mb-1.5" style={{ color: 'var(--color-on-surface)' }}>
            Tag / Category
          </label>
          <select
            value={tag}
            onChange={(e) => setTag(e.target.value)}
            style={{ ...inputStyle, cursor: 'pointer' }}
          >
            {TAGS.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>

        <p className="text-body-sm" style={{ color: 'var(--color-on-surface-variant)' }}>
          You can add documents to this notebook after creating it.
        </p>
      </div>
    </Modal>
  );
}

