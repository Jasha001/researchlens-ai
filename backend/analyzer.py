import unicodedata
import re
from collections import Counter


# ============================================================
# GENERAL STOPWORDS
# IMPORTANT:
# Do NOT remove research words like data/method/model/results.
# They are useful for retrieval.
# ============================================================

STOPWORDS = set("""
the and for with that this from were have has had are was into their
they them which using used use about between through than then also
our we can may more what does did how why who where when
authors author article articles paper papers
is a an of to in on by as at be or it its this these those
""".split())


# ============================================================
# BASIC TEXT HELPERS
# ============================================================

def clean(text):
    text=unicodedata.normalize("NFKC",text or "")
    text=re.sub(r"(?<=\w)-\s*\n\s*(?=\w)","",text)
    return re.sub(r"\s+"," ",text).strip()

def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+",clean(text)) if len(s.strip())>25]

HEADING_RE = re.compile(r"(?mi)^[ \t]*(?:\d+(?:\.\d+)*[.)]?[ \t]+)?(abstract|introduction|background|research methods|methods|methodology|materials and methods|study design|model architecture and training|problem formulation|dataset|data|test|results|findings|experiments|discussion|limitations?|conclusions?|references|acknowledgements?|appendix|future work|training|comparison|chexnet vs. radiologist performance)[ \t]*:?[ \t]*$")

def section(full,names):
    headings=list(HEADING_RE.finditer(full))
    for i,h in enumerate(headings):
        label=clean(h.group(1)).lower()
        if label in [n.lower() for n in names]:
            end=headings[i+1].start() if i+1<len(headings) else len(full)
            return full[h.end():min(end,h.end()+6000)].strip()
    return ""

def metadata(full,filename):
    lines=[clean(x) for x in full.splitlines() if clean(x)]
    title=lines[0] if lines else filename.removesuffix(".pdf")
    first=full[:12000]
    # Publication cues only: sample sizes and years in narrative are not dates.
    patterns=[r"arXiv:\s*(\d{2})\d{2}\.\d+",r"(?:submitted|published|accepted|copyright|©|preprint)[^\n]{0,100}?\b((?:19|20)\d{2})\b",r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+((?:19|20)\d{2})\b",r"\b(?:KDD|ICML|NeurIPS|AAAI|IJCAI)\s+((?:19|20)\d{2})\b"]
    year=None
    for pattern in patterns:
        m=re.search(pattern,first,re.I)
        if m:
            value=m.group(1);year=('20'+value if int(value)<90 else '19'+value) if len(value)==2 else value;break
    doi=re.search(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+",full,re.I)
    return {"title":title[:300],"year":year,"doi":doi.group(0).rstrip(".,)") if doi else None}

# ============================================================
# KEY TERMS
# ============================================================

def terms(full, n=10):

    words = re.findall(
        r"[A-Za-z][A-Za-z-]{4,}",
        full.lower()
    )

    counter = Counter(
        w for w in words
        if w not in STOPWORDS
    )

    return [
        {
            "term": word,
            "count": count
        }
        for word, count in counter.most_common(n)
    ]


# ============================================================
# TOKENIZER FOR RETRIEVAL
# ============================================================

def tokenize(text):

    return set(
        w
        for w in re.findall(
            r"[a-zA-Z][a-zA-Z-]{2,}",
            text.lower()
        )
        if w not in STOPWORDS
    )


# ============================================================
# CHUNK PDF INTO SMALLER PIECES
# ============================================================

def split_chunks(pages, max_chars=1800):

    chunks = []

    for page in pages:

        page_number = page["page"]

        raw_text = page.get("text", "")
        # Reference lists are not experimental evidence; do not merge them into a passage.
        ref=re.search(r"(?mi)^\s*(?:\d+[.]?\s+)?(?:references|bibliography)\s*$",raw_text)
        if ref:raw_text=raw_text[:ref.start()]

        if not raw_text.strip():
            continue

        paragraphs = re.split(
            r"\n\s*\n",
            raw_text
        )

        current = ""

        for paragraph in paragraphs:

            paragraph = clean(paragraph)

            if not paragraph:
                continue

            if len(current) + len(paragraph) + 1 <= max_chars:

                current += " " + paragraph

            else:

                if current:

                    chunks.append({
                        "page": page_number,
                        "text": clean(current)
                    })

                current = paragraph

        if current:

            chunks.append({
                "page": page_number,
                "text": clean(current)
            })

    return chunks


# ============================================================
# QUESTION INTENT
# ============================================================

def detect_question_intent(question):

    q = question.lower()
    for words,intent in [(('ডেটা','dataset','রোগী','নমুনা'),'dataset'),(('পদ্ধতি','মডেল','অ্যালগরিদম'),'method'),(('ফলাফল','নির্ভুলতা','স্কোর'),'result'),(('সীমাবদ্ধ','দুর্বল','ভবিষ্যৎ'),'limitation'),(('উদ্দেশ্য','গবেষণা প্রশ্ন'),'objective')]:
        if any(w in q for w in words):return intent

    if any(
        x in q
        for x in [
            "dataset",
            "data source",
            "what data",
            "data used",
            "sample",
            "participants",
            "patients",
            "subjects",
            "population",
            "cohort",
            "records"
        ]
    ):
        return "dataset"

    if any(
        x in q
        for x in [
            "method",
            "methodology",
            "algorithm",
            "model",
            "architecture",
            "training",
            "analysis",
            "how did the authors",
            "how was the study"
        ]
    ):
        return "method"

    if any(
        x in q
        for x in [
            "result",
            "results",
            "finding",
            "findings",
            "accuracy",
            "auc",
            "performance",
            "outcome",
            "significant"
        ]
    ):
        return "result"

    if any(
        x in q
        for x in [
            "limitation",
            "limitations",
            "weakness",
            "constraint",
            "future work"
        ]
    ):
        return "limitation"

    if any(
        x in q
        for x in [
            "objective",
            "aim",
            "purpose",
            "research question",
            "what did the study investigate",
            "what was the study about"
        ]
    ):
        return "objective"

    if any(
        x in q
        for x in [
            "conclusion",
            "conclude",
            "overall conclusion"
        ]
    ):
        return "conclusion"

    if any(
        x in q
        for x in [
            "author",
            "authors",
            "who wrote",
            "researcher",
            "affiliation"
        ]
    ):
        return "authors"

    return "general"


# ============================================================
# INTENT-SPECIFIC SEARCH TERMS
# ============================================================

INTENT_TERMS = {

    "dataset": [
        "dataset",
        "data",
        "data source",
        "data collection",
        "sample",
        "samples",
        "participants",
        "patients",
        "subjects",
        "population",
        "study population",
        "patient population",
        "cohort",
        "records",
        "medical records",
        "clinical records",
        "database",
        "registry",
        "electronic health record",
        "ehr",
        "retrospective",
        "prospective"
    ],

    "method": [
        "method",
        "methods",
        "methodology",
        "materials",
        "materials and methods",
        "algorithm",
        "model",
        "architecture",
        "training",
        "machine learning",
        "deep learning",
        "regression",
        "statistical analysis",
        "analysis",
        "classification",
        "prediction"
    ],

    "result": [
        "result",
        "results",
        "finding",
        "findings",
        "accuracy",
        "precision",
        "recall",
        "f1",
        "auc",
        "roc",
        "performance",
        "outcome",
        "significant",
        "association",
        "improved",
        "improvement"
    ],

    "limitation": [
        "limitation",
        "limitations",
        "weakness",
        "constraint",
        "future work",
        "generalizability",
        "external validation"
    ],

    "objective": [
        "aim",
        "objective",
        "purpose",
        "investigate",
        "examines",
        "examine",
        "propose",
        "research question",
        "study"
    ],

    "conclusion": [
        "conclusion",
        "conclusions",
        "conclude",
        "overall",
        "future"
    ],

    "authors": [
        "author",
        "authors",
        "affiliation",
        "researcher",
        "department",
        "university",
        "institution"
    ],

    "general": []
}


# ============================================================
# REFERENCE DETECTION
# ============================================================

def reference_score(text):

    t = text.lower()

    score = 0

    # Strong signals
    if "references" in t[:500]:
        score += 8

    if "bibliography" in t[:500]:
        score += 8

    # Citation-heavy text
    citation_patterns = [
        r"\[\d+\]",
        r"\(\d{4}\)",
        r"\bet al\.",
        r"\bdoi\b",
        r"\bpmid\b"
    ]

    for pattern in citation_patterns:

        score += len(
            re.findall(
                pattern,
                t,
                re.I
            )
        )

    return score


# ============================================================
# RETRIEVAL
# ============================================================

def retrieve_chunks(pages, question, top_k=6):

    chunks = split_chunks(pages)

    if not chunks:
        return []

    intent = detect_question_intent(question)

    query_words = tokenize(question)

    intent_terms = INTENT_TERMS.get(
        intent,
        []
    )

    scored = []

    total_pages = len(pages)

    for index, chunk in enumerate(chunks):

        text = chunk["text"]

        text_lower = text.lower()

        text_words = tokenize(text)

        score = 0

        # ----------------------------------------------------
        # 1. Query word overlap
        # ----------------------------------------------------

        overlap = query_words.intersection(
            text_words
        )

        score += len(overlap) * 2


        # ----------------------------------------------------
        # 2. Intent-specific keywords
        # ----------------------------------------------------

        for term in intent_terms:

            if term in text_lower:

                # Longer/more specific terms get more weight
                if len(term.split()) > 1:
                    score += 5
                else:
                    score += 3


        # ----------------------------------------------------
        # 3. Section heading signals
        # ----------------------------------------------------

        first_part = text_lower[:700]

        heading_terms = {

            "dataset": [
                "data",
                "dataset",
                "participants",
                "sample",
                "study population",
                "patient population"
            ],

            "method": [
                "methods",
                "methodology",
                "materials and methods",
                "statistical analysis"
            ],

            "result": [
                "results",
                "findings"
            ],

            "limitation": [
                "limitations",
                "discussion"
            ],

            "objective": [
                "abstract",
                "introduction",
                "objective",
                "aim"
            ],

            "conclusion": [
                "conclusion",
                "conclusions"
            ],

            "authors": [
                "author",
                "affiliation",
                "department"
            ]
        }

        for term in heading_terms.get(
            intent,
            []
        ):

            if term in first_part:
                score += 5


        # ----------------------------------------------------
        # 4. Dataset-specific semantic signals
        # ----------------------------------------------------

        if intent == "dataset":

            dataset_signals = [
                "retrospective study",
                "prospective study",
                "patient records",
                "medical records",
                "clinical records",
                "patient population",
                "study population",
                "included patients",
                "patients were",
                "participants were",
                "data were collected",
                "data was collected",
                "database",
                "registry",
                "cohort"
            ]

            for signal in dataset_signals:

                if signal in text_lower:
                    score += 6


        # ----------------------------------------------------
        # 5. Method-specific signals
        # ----------------------------------------------------

        if intent == "method":

            method_signals = [
                "machine learning",
                "deep learning",
                "logistic regression",
                "random forest",
                "neural network",
                "statistical analysis",
                "cross-validation",
                "training set",
                "test set",
                "validation set"
            ]

            for signal in method_signals:

                if signal in text_lower:
                    score += 5


        # ----------------------------------------------------
        # 6. Results-specific signals
        # ----------------------------------------------------

        if intent == "result":

            result_signals = [
                "accuracy",
                "auc",
                "p-value",
                "p value",
                "confidence interval",
                "odds ratio",
                "sensitivity",
                "specificity",
                "significant"
            ]

            for signal in result_signals:

                if signal in text_lower:
                    score += 4


        # ----------------------------------------------------
        # 7. Reference penalty
        # ----------------------------------------------------

        ref_score = reference_score(text)

        if ref_score >= 12:

            score -= 15

        elif ref_score >= 6:

            score -= 10

        elif ref_score >= 3:

            score -= 5


        # ----------------------------------------------------
        # 8. Page-position hints
        # ----------------------------------------------------

        page = chunk["page"]

        if intent in [
            "authors",
            "objective"
        ]:

            if page <= 2:
                score += 4


        if intent in [
            "dataset",
            "method"
        ]:

            # Methods/data usually appear earlier
            if page <= max(
                4,
                total_pages // 2
            ):
                score += 2


        if intent == "result":

            # Results usually after methods
            if page >= 2:
                score += 1


        if intent == "conclusion":

            if page >= max(
                1,
                total_pages - 2
            ):
                score += 4


        # ----------------------------------------------------
        # Save
        # ----------------------------------------------------

        scored.append({

            "page": page,

            "text": text,

            "score": score,

            "index": index

        })


    # ========================================================
    # SORT
    # ========================================================

    scored.sort(
        key=lambda x: x["score"],
        reverse=True
    )


    # ========================================================
    # REMOVE LOW QUALITY RESULTS
    # ========================================================

    useful = [
        item
        for item in scored
        if item["score"] > 0
    ]


    # ========================================================
    # SELECT DIVERSE PAGES
    # ========================================================

    selected = []

    pages_seen = set()

    for item in useful:

        page = item["page"]

        if page in pages_seen:
            continue

        selected.append(item)

        pages_seen.add(page)

        if len(selected) >= top_k:
            break


    return selected


# ============================================================
# EVIDENCE EXTRACTION
# ============================================================

def trim_excerpt(text):
    text=clean(text)
    if text and text[-1] not in '.!?':
        last=max(text.rfind('. '),text.rfind('! '),text.rfind('? '))
        if last>=60:text=text[:last+1]
    return text

def evidence(pages,text):
    needle=clean(text)
    if not needle:return []
    hits=[]
    for page in pages:
        body=clean(page['text'])
        # Exact text containment anchors evidence to its actual source.
        anchor=needle[:180]
        at=body.find(anchor)
        if at>=0:
            hits.append({'page':page['page'],'score':len(anchor),'snippet':trim_excerpt(body[at:at+min(len(needle),1500)])})
    return hits[:3]

# ============================================================
# DOCUMENT ANALYSIS
# ============================================================

def analyze_document(filename, pages):

    first_lines=[clean(x) for x in pages[0]["text"].splitlines() if clean(x)] if pages else []
    running=first_lines[0] if first_lines else ""
    bodies=[]
    for index,p in enumerate(pages):
        lines=p["text"].splitlines()
        if index: lines=[x for x in lines if not (clean(x)==running or clean(x).startswith(running+" with "))]
        bodies.append("\n".join(lines))
    full="\n".join(bodies)

    ss = sentences(full)

    meta = metadata(
        full,
        filename
    )


    abstract = section(
        full,
        ["abstract"]
    )


    methods = section(
        full,
        [
            "methodology",
            "methods",
            "materials and methods",
            "study design", "research methods", "model architecture and training"
        ]
    )


    results = section(
        full,
        [
            "results",
            "findings", "test"
        ]
    )


    limits = section(
        full,
        [
            "limitations",
            "limitation"
        ]
    )


    ss = sentences(abstract) if abstract else []
    # Prefer literal metric-bearing prose when there is no dedicated Results heading.
    if not section(full,["results","findings"]):
        candidates=[]
        for p in pages:
            for paragraph in re.split(r"\n\s*\n",p['text']):
                t=clean(paragraph)
                if len(t)>90 and re.search(r"(?:achieves|achieved|outperforms|exceeds|F1 score of|AUROC of)",t,re.I) and re.search(r"\d+\.\d+",t): candidates.append(t)
        results="\n\n".join(candidates[:3]) or ""
    if limits:
        # Figure captions may interrupt a limitations paragraph at a page break.
        blocks=re.split(r"\n\s*\n",limits)
        blocks=[b for b in blocks if not re.match(r"(?:Figure\s+\d|\([a-f]\)\s+Patient)",clean(b),re.I)]
        limits="\n\n".join(blocks)
        limits=re.split(r"(?m)^[ \t]*\d+(?:\.\d+)*[.][ \t]+[A-Z][^\n]{2,100}$",limits)[0].strip()


    # --------------------------------------------------------
    # Research question
    # --------------------------------------------------------

    rq = [
        s
        for s in ss
        if any(
            x in s.lower()
            for x in [
                "aim",
                "objective",
                "purpose",
                "investigate",
                "examine",
                "propose", "we develop", "we present", "we introduce", "we evaluate"
            ]
        )
    ]


    # --------------------------------------------------------
    # Result highlights
    # --------------------------------------------------------

    rh = [
        s
        for s in ss
        if any(
            x in s.lower()
            for x in [
                "significant",
                "accuracy",
                "auc",
                "improved",
                "found",
                "outperformed",
                "associated"
            ]
        )
    ]


    # --------------------------------------------------------
    # Evidence
    # --------------------------------------------------------

    ev = []

    for label, text in [
        ("Abstract", abstract),
        ("Methodology", methods),
        ("Results", results),
        ("Limitations", limits)
    ]:

        if text:

            hits = evidence(
                pages,
                text
            )

            if hits:

                ev.append({

                    "label": label,

                    "page": hits[0]["page"],

                    "snippet": hits[0]["snippet"]

                })


    # --------------------------------------------------------
    # Methodology checklist
    # --------------------------------------------------------

    checklist = {

        "Dataset/sample described":
            bool(
                re.search(
                    r"dataset|participants|sample size|subjects|patients|population|cohort",
                    full,
                    re.I
                )
            ),

        "Train/test or validation described":
            bool(
                re.search(
                    r"train|test set|validation|cross-validation|cross validation",
                    full,
                    re.I
                )
            ),

        "Evaluation metrics reported":
            bool(
                re.search(
                    r"accuracy|precision|recall|f1|auc|roc|sensitivity|specificity",
                    full,
                    re.I
                )
            ),

        "Baseline/comparison reported":
            bool(
                re.search(
                    r"baseline|benchmark|compared with|comparison",
                    full,
                    re.I
                )
            ),

        "Limitations discussed":
            bool(limits),

        "Reproducibility details visible":
            bool(
                re.search(
                    r"code available|github|repository|implementation|hyperparameter",
                    full,
                    re.I
                )
            )
    }


    # --------------------------------------------------------
    # Research gaps
    # --------------------------------------------------------

    gaps = [

        "Check whether findings are externally validated on an independent dataset.",

        "Check whether subgroup or fairness analysis is reported.",

        "Check whether baseline comparisons are sufficiently strong and current.",

        "Check whether data and code are available for reproducibility.",

        "Check whether uncertainty measures such as confidence intervals are reported."
    ]


    # --------------------------------------------------------
    # Citation
    # --------------------------------------------------------

    citation = f'{meta["title"]}.'

    if meta["year"]:

        citation += f' ({meta["year"]}).'


    # --------------------------------------------------------
    # Final document object
    # --------------------------------------------------------

    return {

        "analysis_version": 5,
        "filename": filename,

        "page_count": len(pages),

        "metadata": meta,

        "abstract":
            clean(abstract)[:2500],

        "summary":
            (
                ss
                or ["No abstract heading was confidently identified. Use the evidence-led explanation."]
            )[:5],

        "research_question":
            (
                rq[0]
                if rq
                else
                "No explicit research question was confidently identified."
            )[:1000],

        "methodology":
            clean(methods)[:3000]
            or
            "No dedicated methodology section was confidently identified.",

        "results":
            clean(results)[:3000]
            or
            "No dedicated results section was confidently identified.",

        "limitations":
            trim_excerpt(clean(limits)[:2500])
            or
            "No dedicated limitations section was confidently identified.",

        "key_terms":
            terms(unicodedata.normalize("NFKC", full)),

        "result_highlights":
            rh[:6],

        "evidence":
            ev,

        "methodology_check":
            checklist,

        "research_gaps":
            gaps,

        "citation": {

            "apa": citation,

            "mla": citation,

            "ieee": citation

        },

        "pages":
            pages
    }


# ============================================================
# LOCAL QUESTION ANSWERING FALLBACK
# ============================================================

def answer_question(doc, q, mode):

    pages = doc.get(
        "pages",
        []
    )

    chunks = retrieve_chunks(
        pages,
        q,
        top_k=6
    )


    if not chunks:

        return {

            "answer":
                "Insufficient evidence in the provided paper.",

            "evidence": [],

            "mode": mode,

            "grounded": True
        }


    return {

        "answer":
            "Relevant evidence was retrieved from the paper.",

        "evidence": [

            {
                "page": c["page"],

                "snippet": c["text"][:700]

            }

            for c in chunks

        ],

        "mode": mode,

        "grounded": True
    }


# ============================================================
# PAPER COMPARISON
# ============================================================

def compare_documents(docs):

    return {

        "papers": [

            {

                "title":
                    d.get(
                        "metadata",
                        {}
                    ).get(
                        "title"
                    )
                    or
                    d.get(
                        "filename"
                    ),

                "year":
                    d.get(
                        "metadata",
                        {}
                    ).get(
                        "year"
                    ),

                "methodology":
                    clean(
                        d.get(
                            "methodology",
                            ""
                        )
                    )[:400],

                "result":
                    clean(
                        d.get(
                            "results",
                            ""
                        )
                    )[:400],

                "limitation":
                    clean(
                        d.get(
                            "limitations",
                            ""
                        )
                    )[:300]
            }

            for d in docs

        ]
    }