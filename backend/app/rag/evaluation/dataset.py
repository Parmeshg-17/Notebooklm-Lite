from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class EvaluationTestCase:
    id: str
    category: str
    question: str
    expected_answer: str
    expected_pages: List[int]
    expected_keywords: List[str]
    should_refuse: bool = False
    supporting_passage: Optional[str] = None


EVALUATION_DATASET: List[EvaluationTestCase] = [
    # 1. Exact Factual (5)
    EvaluationTestCase(
        id="fact_01",
        category="factual",
        question="Who cofounded OpenAI after authoring the AlexNet paper?",
        expected_answer="Ilya Sutskever cofounded OpenAI after authoring the AlexNet paper.",
        expected_pages=[13],
        expected_keywords=["ilya", "sutskever", "alexnet", "openai"],
        should_refuse=False,
    ),
    EvaluationTestCase(
        id="fact_02",
        category="factual",
        question="What is the title of Chapter 9 in the book AI Engineering?",
        expected_answer="Chapter 9 is titled Inference Optimization.",
        expected_pages=[11],
        expected_keywords=["inference", "optimization"],
        should_refuse=False,
    ),
    EvaluationTestCase(
        id="fact_03",
        category="factual",
        question="Who is the author of the book AI Engineering?",
        expected_answer="The author is Chip Huyen.",
        expected_pages=[3, 4, 6],
        expected_keywords=["chip", "huyen"],
        should_refuse=False,
    ),
    EvaluationTestCase(
        id="fact_04",
        category="factual",
        question="What publisher published the book AI Engineering?",
        expected_answer="O'Reilly Media published the book.",
        expected_pages=[6],
        expected_keywords=["o'reilly"],
        should_refuse=False,
    ),
    EvaluationTestCase(
        id="fact_05",
        category="factual",
        question="What is the ISBN of the book AI Engineering?",
        expected_answer="The ISBN is 978-1-098-16630-4.",
        expected_pages=[2],
        expected_keywords=["978-1-098-16630-4", "isbn"],
        should_refuse=False,
    ),

    # 2. Conceptual Questions (5)
    EvaluationTestCase(
        id="concept_06",
        category="conceptual",
        question="Why is memory bandwidth a major bottleneck during autoregressive token generation?",
        expected_answer="Each token generation step requires transferring the entire model's parameters from accelerator memory to compute units.",
        expected_pages=[452],
        expected_keywords=["memory", "bandwidth", "token", "generation", "transfer", "compute"],
        should_refuse=False,
    ),
    EvaluationTestCase(
        id="concept_07",
        category="conceptual",
        question="What contributes significantly to the memory footprint of transformer models alongside model weights?",
        expected_answer="The KV cache contributes significantly to the memory footprint.",
        expected_pages=[353],
        expected_keywords=["kv cache", "memory", "footprint"],
        should_refuse=False,
    ),
    EvaluationTestCase(
        id="concept_08",
        category="conceptual",
        question="How does speculative decoding improve inference latency for language models?",
        expected_answer="Speculative decoding uses a smaller draft model to generate candidate tokens which are then verified in parallel by the target model.",
        expected_pages=[452, 453],
        expected_keywords=["speculative", "decoding", "draft", "verify", "parallel", "latency"],
        should_refuse=False,
    ),
    EvaluationTestCase(
        id="concept_09",
        category="conceptual",
        question="What are common failure modes and challenges in AI agent planning?",
        expected_answer="Common challenges include infinite loops, tool execution errors, plan drift, and compounding errors across multiple steps.",
        expected_pages=[281, 298],
        expected_keywords=["agent", "planning", "failure", "tool"],
        should_refuse=False,
    ),
    EvaluationTestCase(
        id="concept_10",
        category="conceptual",
        question="What is the primary advantage of Low-Rank Adaptation (LoRA) for model fine-tuning?",
        expected_answer="LoRA freezes base weights and trains low-rank decomposition matrices, significantly reducing memory and trainable parameter count.",
        expected_pages=[353, 371],
        expected_keywords=["lora", "adapter", "low-rank", "trainable"],
        should_refuse=False,
    ),

    # 3. Multi-page Questions (5)
    EvaluationTestCase(
        id="multi_11",
        category="multi_page",
        question="How does the text describe multimodal RAG beyond plain text?",
        expected_answer="Multimodal RAG incorporates images, tables, diagrams, structured schemas, and cross-modal embedding spaces.",
        expected_pages=[10, 273, 274],
        expected_keywords=["rag", "multimodal", "text"],
        should_refuse=False,
    ),
    EvaluationTestCase(
        id="multi_12",
        category="multi_page",
        question="What are the trade-offs between prompt engineering, RAG, and fine-tuning for adapting foundation models?",
        expected_answer="Prompt engineering offers rapid prototyping but limited capacity; RAG provides dynamic real-time retrieval; fine-tuning specializes behavior at higher compute cost.",
        expected_pages=[10, 305, 306],
        expected_keywords=["prompt", "rag", "finetuning", "trade-off"],
        should_refuse=False,
    ),
    EvaluationTestCase(
        id="multi_13",
        category="multi_page",
        question="How are LLM evaluation pipelines structured according to the text?",
        expected_answer="LLM evaluation utilizes deterministic unit tests, AI-as-a-judge criteria, human evaluations, and benchmark tracking.",
        expected_pages=[166, 231],
        expected_keywords=["evaluation", "pipeline", "metrics"],
        should_refuse=False,
    ),
    EvaluationTestCase(
        id="multi_14",
        category="multi_page",
        question="What strategies are recommended for document chunking and context management in retrieval?",
        expected_answer="Techniques include fixed character chunking with overlap, semantic boundary chunking, and metadata preservation.",
        expected_pages=[260, 268],
        expected_keywords=["chunk", "retrieval", "context"],
        should_refuse=False,
    ),
    EvaluationTestCase(
        id="multi_15",
        category="multi_page",
        question="What are the pros and cons of local on-device model deployment versus cloud API hosting?",
        expected_answer="On-device ensures privacy and eliminates egress latency/cost but faces hardware constraints; cloud hosting allows largest models and elastic scaling.",
        expected_pages=[214, 215],
        expected_keywords=["device", "data", "pros", "cons", "table"],
        should_refuse=False,
    ),

    # 4. Cross-Document / Comparison Questions (5)
    EvaluationTestCase(
        id="comp_16",
        category="comparison",
        question="How does quantization compare to pruning and knowledge distillation for model compression?",
        expected_answer="Quantization reduces numeric precision (e.g. FP16 to INT8); pruning removes weights; distillation transfers knowledge from a teacher to a student model.",
        expected_pages=[350, 353],
        expected_keywords=["quantization", "model", "memory"],
        should_refuse=False,
    ),
    EvaluationTestCase(
        id="comp_17",
        category="comparison",
        question="Compare dense semantic retrieval with sparse lexical BM25 retrieval.",
        expected_answer="Dense retrieval captures semantic synonyms and cross-lingual meaning; lexical BM25 excels at exact keyword matching, technical IDs, and rare jargon.",
        expected_pages=[260, 268],
        expected_keywords=["retrieval", "dense", "search"],
        should_refuse=False,
    ),
    EvaluationTestCase(
        id="comp_18",
        category="comparison",
        question="Compare AI-as-a-judge evaluation with human evaluation guidelines.",
        expected_answer="AI-as-a-judge provides fast automated scoring but suffers from verbosity and position bias; human evaluation is grounded but slower and costly.",
        expected_pages=[166, 403],
        expected_keywords=["judge", "evaluation", "guidelines"],
        should_refuse=False,
    ),
    EvaluationTestCase(
        id="comp_19",
        category="comparison",
        question="What is the list price of the physical book?",
        expected_answer="The list price is US $79.99 / CAN $99.99 printed on page 2.",
        expected_pages=[2],
        expected_keywords=["79.99", "price", "isbn"],
        should_refuse=False,
    ),
    EvaluationTestCase(
        id="comp_20",
        category="comparison",
        question="Is model scaling always preferable to smaller specialized models?",
        expected_answer="Scaling up increases accuracy on general tasks but incurs severe memory and latency costs; smaller specialized models frequently win on speed and cost.",
        expected_pages=[13, 214],
        expected_keywords=["scale", "model", "latency"],
        should_refuse=False,
    ),

    # 5. Unanswerable / Insufficient Evidence Questions (5 - Must Refuse)
    EvaluationTestCase(
        id="unans_21",
        category="unanswerable",
        question="What is the secret 11 herbs and spices recipe for Kentucky Fried Chicken?",
        expected_answer="REFUSAL",
        expected_pages=[],
        expected_keywords=[],
        should_refuse=True,
    ),
    EvaluationTestCase(
        id="unans_22",
        category="unanswerable",
        question="What was the closing stock price of Tesla on December 15, 2025?",
        expected_answer="REFUSAL",
        expected_pages=[],
        expected_keywords=[],
        should_refuse=True,
    ),
    EvaluationTestCase(
        id="unans_23",
        category="unanswerable",
        question="What are the exact dimensions and weight of the Apollo 11 lunar module fuel tanks?",
        expected_answer="REFUSAL",
        expected_pages=[],
        expected_keywords=[],
        should_refuse=True,
    ),
    EvaluationTestCase(
        id="unans_24",
        category="unanswerable",
        question="What dosage of amoxicillin is prescribed for adult streptococcal pharyngitis in this book?",
        expected_answer="REFUSAL",
        expected_pages=[],
        expected_keywords=[],
        should_refuse=True,
    ),
    EvaluationTestCase(
        id="unans_25",
        category="unanswerable",
        question="What is the terminal gate departure schedule for United Airlines flight 853 from Tokyo?",
        expected_answer="REFUSAL",
        expected_pages=[],
        expected_keywords=[],
        should_refuse=True,
    ),

    # 6. Unrelated Questions (5 - Must Refuse)
    EvaluationTestCase(
        id="unrel_26",
        category="unrelated",
        question="How do you make authentic Neapolitan pizza dough with sourdough starter at home?",
        expected_answer="REFUSAL",
        expected_pages=[],
        expected_keywords=[],
        should_refuse=True,
    ),
    EvaluationTestCase(
        id="unrel_27",
        category="unrelated",
        question="What is the capital city and official currency of Madagascar?",
        expected_answer="REFUSAL",
        expected_pages=[],
        expected_keywords=[],
        should_refuse=True,
    ),
    EvaluationTestCase(
        id="unrel_28",
        category="unrelated",
        question="Who scored the winning goal in the 1998 FIFA World Cup final?",
        expected_answer="REFUSAL",
        expected_pages=[],
        expected_keywords=[],
        should_refuse=True,
    ),
    EvaluationTestCase(
        id="unrel_29",
        category="unrelated",
        question="How do chlorophyll molecules absorb photon wavelengths during light-dependent photosynthetic reactions?",
        expected_answer="REFUSAL",
        expected_pages=[],
        expected_keywords=[],
        should_refuse=True,
    ),
    EvaluationTestCase(
        id="unrel_30",
        category="unrelated",
        question="What are the clinical ultrasound criteria for acute appendicitis in pediatric emergency care?",
        expected_answer="REFUSAL",
        expected_pages=[],
        expected_keywords=[],
        should_refuse=True,
    ),
]

