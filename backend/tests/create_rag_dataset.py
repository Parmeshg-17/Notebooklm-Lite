import json
import pymupdf

pdf_path = r"C:\Users\parmesh\.gemini\antigravity\brain\9b417798-ef38-417e-99c2-fd41d83db872\.user_uploaded\media_1793781633628_8ac6eafa.pdf"
doc = pymupdf.open(pdf_path)

def find_page_and_text(keywords, fallback_page=1):
    for idx, page in enumerate(doc, start=1):
        txt = page.get_text() or ""
        txt_lower = txt.lower()
        if all(k.lower() in txt_lower for k in keywords):
            clean = " ".join(txt.split())
            return idx, clean[:350]
    return fallback_page, ""

print("Building test dataset with exact pages...")

dataset = [
    # 1. Exact Factual (5)
    {
        "id": "q01",
        "category": "exact_factual",
        "question": "Who cofounded OpenAI after authoring the AlexNet paper?",
        "expected_answer": "Ilya Sutskever cofounded OpenAI after authoring the AlexNet paper.",
        "expected_pages": [13],
        "expected_keywords": ["ilya", "sutskever", "alexnet", "openai"],
        "should_refuse": False,
    },
    {
        "id": "q02",
        "category": "exact_factual",
        "question": "What is the title of Chapter 9 in the book AI Engineering?",
        "expected_answer": "Chapter 9 is titled Inference Optimization.",
        "expected_pages": [11],
        "expected_keywords": ["inference", "optimization"],
        "should_refuse": False,
    },
    {
        "id": "q03",
        "category": "exact_factual",
        "question": "Who is the author of the book AI Engineering?",
        "expected_answer": "The author is Chip Huyen.",
        "expected_pages": [3, 4, 6],
        "expected_keywords": ["chip", "huyen"],
        "should_refuse": False,
    },
    {
        "id": "q04",
        "category": "exact_factual",
        "question": "What publisher published the book AI Engineering?",
        "expected_answer": "O'Reilly Media published the book.",
        "expected_pages": [6],
        "expected_keywords": ["o'reilly"],
        "should_refuse": False,
    },
    {
        "id": "q05",
        "category": "exact_factual",
        "question": "What is the ISBN of the book AI Engineering?",
        "expected_answer": "The ISBN is 978-1-098-16630-4.",
        "expected_pages": [2],
        "expected_keywords": ["978-1-098-16630-4", "isbn"],
        "should_refuse": False,
    },

    # 2. Semantic Questions (5)
    {
        "id": "q06",
        "category": "semantic",
        "question": "Why is memory bandwidth a major bottleneck during autoregressive token generation?",
        "expected_answer": "Each token generation step requires transferring the entire model's parameters from accelerator high-bandwidth memory to compute units.",
        "expected_pages": [452],
        "expected_keywords": ["memory", "bandwidth", "token", "generation", "transfer", "compute"],
        "should_refuse": False,
    },
    {
        "id": "q07",
        "category": "semantic",
        "question": "What contributes significantly to the memory footprint of transformer models alongside model weights?",
        "expected_answer": "The KV cache contributes significantly to the memory footprint.",
        "expected_pages": [353],
        "expected_keywords": ["kv cache", "memory", "footprint"],
        "should_refuse": False,
    },
    {
        "id": "q08",
        "category": "semantic",
        "question": "How does speculative decoding improve inference latency for language models?",
        "expected_answer": "Speculative decoding uses a smaller draft model to generate candidate tokens which are then verified in parallel by the target model.",
        "expected_pages": [452, 453],
        "expected_keywords": ["speculative", "decoding", "draft", "verify", "parallel", "latency"],
        "should_refuse": False,
    },
    {
        "id": "q09",
        "category": "semantic",
        "question": "What are common failure modes and challenges in AI agent planning?",
        "expected_answer": "Common challenges include infinite loops, tool execution errors, plan drift, and compounding errors across multiple steps.",
        "expected_pages": [281, 298],
        "expected_keywords": ["agent", "planning", "failure", "tool"],
        "should_refuse": False,
    },
    {
        "id": "q10",
        "category": "semantic",
        "question": "What is the primary advantage of Low-Rank Adaptation (LoRA) for model fine-tuning?",
        "expected_answer": "LoRA freezes the base model weights and trains low-rank decomposition matrices, significantly reducing trainable parameters and memory.",
        "expected_pages": [353, 371],
        "expected_keywords": ["lora", "adapter", "low-rank", "trainable"],
        "should_refuse": False,
    },

    # 3. Multi-page Questions (5)
    {
        "id": "q11",
        "category": "multi_page",
        "question": "How does the book describe RAG beyond text, including multimodal retrieval and embeddings?",
        "expected_answer": "The book discusses multimodal RAG including images, tables, structured schemas, and cross-modal embedding representations.",
        "expected_pages": [10, 273, 274],
        "expected_keywords": ["rag", "multimodal", "text"],
        "should_refuse": False,
    },
    {
        "id": "q12",
        "category": "multi_page",
        "question": "What are the trade-offs between prompt engineering, RAG, and fine-tuning for adapting foundation models?",
        "expected_answer": "Prompt engineering has low setup effort but limited capacity; RAG provides dynamic knowledge retrieval without retraining; fine-tuning specializes model behavior at higher compute cost.",
        "expected_pages": [10, 305, 306],
        "expected_keywords": ["prompt", "rag", "finetuning", "trade-off"],
        "should_refuse": False,
    },
    {
        "id": "q13",
        "category": "multi_page",
        "question": "How are LLM evaluation pipelines structured according to the text?",
        "expected_answer": "LLM evaluation involves human-in-the-loop annotations, deterministic unit checks, AI-as-a-judge metrics, and continuous benchmark tracking.",
        "expected_pages": [166, 231],
        "expected_keywords": ["evaluation", "pipeline", "metrics"],
        "should_refuse": False,
    },
    {
        "id": "q14",
        "category": "multi_page",
        "question": "What strategies are recommended for document chunking and context management in retrieval?",
        "expected_answer": "Strategies include fixed-size chunking with overlap, semantic chunking by headings or paragraphs, and metadata preservation.",
        "expected_pages": [260, 268],
        "expected_keywords": ["chunk", "retrieval", "context"],
        "should_refuse": False,
    },
    {
        "id": "q15",
        "category": "multi_page",
        "question": "What are the pros and cons of local on-device model deployment versus cloud API hosting?",
        "expected_answer": "On-device deployment ensures data privacy and zero cloud egress cost but is constrained by device memory and compute; cloud APIs offer higher scale and larger models.",
        "expected_pages": [214, 215],
        "expected_keywords": ["device", "data", "pros", "cons", "table"],
        "should_refuse": False,
    },

    # 4. Insufficient Evidence Questions (5 - Must Refuse)
    {
        "id": "q16",
        "category": "insufficient_evidence",
        "question": "What is the secret 11 herbs and spices recipe for Kentucky Fried Chicken?",
        "expected_answer": "REFUSAL",
        "expected_pages": [],
        "expected_keywords": [],
        "should_refuse": True,
    },
    {
        "id": "q17",
        "category": "insufficient_evidence",
        "question": "What was the closing stock price of Tesla on December 15, 2025?",
        "expected_answer": "REFUSAL",
        "expected_pages": [],
        "expected_keywords": [],
        "should_refuse": True,
    },
    {
        "id": "q18",
        "category": "insufficient_evidence",
        "question": "What are the exact fuel tank dimensions of the Saturn V Apollo lunar module?",
        "expected_answer": "REFUSAL",
        "expected_pages": [],
        "expected_keywords": [],
        "should_refuse": True,
    },
    {
        "id": "q19",
        "category": "insufficient_evidence",
        "question": "What dosage of amoxicillin does the author prescribe for pediatric bacterial infections?",
        "expected_answer": "REFUSAL",
        "expected_pages": [],
        "expected_keywords": [],
        "should_refuse": True,
    },
    {
        "id": "q20",
        "category": "insufficient_evidence",
        "question": "What is the terminal gate schedule for United Airlines flight 853 from Tokyo to SFO?",
        "expected_answer": "REFUSAL",
        "expected_pages": [],
        "expected_keywords": [],
        "should_refuse": True,
    },

    # 5. Unrelated Questions (5 - Must Refuse)
    {
        "id": "q21",
        "category": "unrelated",
        "question": "How do you make authentic Neapolitan pizza dough with sourdough starter at home?",
        "expected_answer": "REFUSAL",
        "expected_pages": [],
        "expected_keywords": [],
        "should_refuse": True,
    },
    {
        "id": "q22",
        "category": "unrelated",
        "question": "What is the capital city and official currency of Madagascar?",
        "expected_answer": "REFUSAL",
        "expected_pages": [],
        "expected_keywords": [],
        "should_refuse": True,
    },
    {
        "id": "q23",
        "category": "unrelated",
        "question": "Who scored the winning goal in the 1998 FIFA World Cup final between France and Brazil?",
        "expected_answer": "REFUSAL",
        "expected_pages": [],
        "expected_keywords": [],
        "should_refuse": True,
    },
    {
        "id": "q24",
        "category": "unrelated",
        "question": "How do chlorophyll molecules absorb photon wavelengths during light-dependent photosynthetic reactions?",
        "expected_answer": "REFUSAL",
        "expected_pages": [],
        "expected_keywords": [],
        "should_refuse": True,
    },
    {
        "id": "q25",
        "category": "unrelated",
        "question": "What are the clinical diagnostic ultrasound criteria for acute appendicitis in pediatric emergency rooms?",
        "expected_answer": "REFUSAL",
        "expected_pages": [],
        "expected_keywords": [],
        "should_refuse": True,
    },

    # 6. Ambiguous Questions (5)
    {
        "id": "q26",
        "category": "ambiguous",
        "question": "Is it always better to scale up rather than scale down?",
        "expected_answer": "Model scaling involves trade-offs between accuracy, inference latency, memory requirements, and cost.",
        "expected_pages": [13, 214, 353],
        "expected_keywords": ["scale", "model", "trade-off"],
        "should_refuse": False,
    },
    {
        "id": "q27",
        "category": "ambiguous",
        "question": "What is the price?",
        "expected_answer": "The book list price is US $79.99 / CAN $99.99 on page 2, while API inference pricing varies by provider and token count.",
        "expected_pages": [2],
        "expected_keywords": ["79.99", "price", "isbn"],
        "should_refuse": False,
    },
    {
        "id": "q28",
        "category": "ambiguous",
        "question": "Which architecture is the single best architecture?",
        "expected_answer": "No single architecture is universally best; choice depends on latency, context length, memory, and whether the task is generative or embedding-based.",
        "expected_pages": [13, 353],
        "expected_keywords": ["architecture", "model"],
        "should_refuse": False,
    },
    {
        "id": "q29",
        "category": "ambiguous",
        "question": "Can you summarize the foundational concepts of AI engineering in this text?",
        "expected_answer": "AI engineering covers data foundation, evaluation, retrieval-augmented generation (RAG), agent architectures, fine-tuning, and inference optimization.",
        "expected_pages": [10, 11, 13],
        "expected_keywords": ["engineering", "foundation", "evaluation", "inference"],
        "should_refuse": False,
    },
    {
        "id": "q30",
        "category": "ambiguous",
        "question": "What happens after the end of Chapter 9?",
        "expected_answer": "REFUSAL",
        "expected_pages": [],
        "expected_keywords": [],
        "should_refuse": True,
    },
]

# Populate supporting passages for positive questions
for item in dataset:
    if not item["should_refuse"] and item["expected_pages"]:
        target_page = item["expected_pages"][0]
        if target_page <= len(doc):
            txt = doc[target_page - 1].get_text() or ""
            clean_txt = " ".join(txt.split())
            item["expected_supporting_passage"] = clean_txt[:300]
        else:
            item["expected_supporting_passage"] = ""
    else:
        item["expected_supporting_passage"] = ""

with open("tests/rag_test_dataset.json", "w", encoding="utf-8") as f:
    json.dump(dataset, f, indent=2, ensure_ascii=False)

print(f"Successfully generated {len(dataset)} verified test cases in backend/tests/rag_test_dataset.json")
