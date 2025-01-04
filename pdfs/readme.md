**Priority-Weighted Ground Truth for RAG System: Report**

### **Overview**
This report outlines the creation of a priority-weighted Ground Truth dataset for a Retrieval-Augmented Generation (RAG) system. The focus is on 8 critical documents relevant to defense acquisition, lifecycle management, and research processes. The Ground Truth dataset prioritizes high-importance documents based on assigned weights, ensuring optimal query representation.

---

### **Key Documents and Assigned Weights**
| **Document**                           | **Weight** | **Rationale**                                                                 |
|----------------------------------------|------------|-------------------------------------------------------------------------------|
| 방위사업관리규정                        | 5          | Central to all acquisition processes, lifecycle management, and procurement. |
| 국방전력발전업무훈령                    | 4          | Defines priorities for force development and resource planning.              |
| 국방과학기술혁신 촉진법                 | 4          | Core for R&D and innovation in defense technologies.                         |
| 국방기술연구개발사업 업무처리 지침       | 3          | Details R&D project workflows and evaluation.                                |
| 총수명주기관리업무훈령                  | 3          | Provides lifecycle management standards for defense systems.                 |
| 민·군기술협력사업 촉진법                | 2          | Promotes civilian-military collaboration and technology transfer.            |
| 국방획득정보체계 운영 및 관리업무 훈령   | 2          | Guides acquisition-related information systems.                              |
| 방위산업육성 지원사업 공통 운영규정      | 1          | Supports domestic defense industries and SMEs.                               |

---

### **Query Distribution**
Queries are distributed according to document weight to ensure proportional representation:

| **Document**                           | **Weight** | **Proportion (%)** | **Number of Queries (Total: 100)** |
|----------------------------------------|------------|---------------------|------------------------------------|
| 방위사업관리규정                        | 5          | 25%                 | 25                                 |
| 국방전력발전업무훈령                    | 4          | 20%                 | 20                                 |
| 국방과학기술혁신 촉진법                 | 4          | 20%                 | 20                                 |
| 국방기술연구개발사업 업무처리 지침       | 3          | 15%                 | 15                                 |
| 총수명주기관리업무훈령                  | 3          | 10%                 | 10                                 |
| 민·군기술협력사업 촉진법                | 2          | 5%                  | 5                                  |
| 국방획득정보체계 운영 및 관리업무 훈령   | 2          | 3%                  | 3                                  |
| 방위산업육성 지원사업 공통 운영규정      | 1          | 2%                  | 2                                  |

---

### **Query Examples**
**1. 방위사업관리규정 (25 Queries)**
- "무기체계 소요제기 절차"
- "방위사업 예산 관리 기준"
- "사업 관리 단계별 요건"

**2. 국방전력발전업무훈령 (20 Queries)**
- "전력발전 우선순위 설정 기준"
- "합참 제출 서류 작성 요령"
- "전력발전 검토 절차"

**3. 국방과학기술혁신 촉진법 (20 Queries)**
- "기술혁신 과제 평가 절차"
- "민군 협력 기술 이전 기준"

**4. 국방기술연구개발사업 업무처리 지침 (15 Queries)**
- "R&D 과제 관리 절차"
- "연구개발 단계별 평가 기준"

**5. 총수명주기관리업무훈령 (10 Queries)**
- "RAM 데이터 관리 기준"
- "수명주기 단계별 관리 절차"

**6. 민·군기술협력사업 촉진법 (5 Queries)**
- "민군 협력 과제 평가 절차"

**7. 국방획득정보체계 운영 및 관리업무 훈령 (3 Queries)**
- "DAIS 데이터 관리 방침"

**8. 방위산업육성 지원사업 공통 운영규정 (2 Queries)**
- "방위산업 육성 정책 방향"

---

### **Implementation Plan**
1. **Data Collection**: Gather text and metadata for the top 8 documents.
2. **Query Generation**: Create 100 priority-weighted queries using the distribution table.
3. **Ground Truth Creation**: Match each query with relevant sections or articles from the documents.
4. **Evaluation**:
   - Measure system precision and recall using the Ground Truth.
   - Validate the proportional representation of high-priority documents.

---

### **Benefits of the Weighted Approach**
- **Focus on High-Impact Areas**: Ensures critical documents like "방위사업관리규정" dominate the dataset.
- **Efficient Scalability**: Allows for gradual inclusion of lower-priority documents as needed.
- **Practical Relevance**: Aligns Ground Truth with user scenarios and practical defense workflows.

---

Let me know if further adjustments or additional details are needed!

