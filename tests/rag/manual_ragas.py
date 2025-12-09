"""
Test RAGAS basic functionality with existing RAG system
"""

import asyncio

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def test_ragas_basic():
    """Test basic RAGAS evaluation with sample data"""
    from datasets import Dataset
    from ragas import evaluate
    from ragas.metrics import (
        answer_relevancy,
        context_precision,
        context_recall,
        faithfulness,
    )

    # Sample test data simulating RAG output
    test_data = {
        "question": [
            "如何準備軟體工程師面試？",
            "轉職到科技業需要什麼準備？",
        ],
        "answer": [
            "準備軟體工程師面試需要幾個步驟：1. 練習演算法題目，熟悉常見的資料結構和演算法。2. 準備系統設計問題，了解大規模系統的架構。3. 複習程式語言基礎知識。4. 準備行為面試問題。",
            "轉職到科技業需要：1. 學習相關技術技能，如程式語言、框架等。2. 建立個人專案作品集。3. 參與開源專案或技術社群。4. 準備履歷和面試。5. 建立人脈網絡。",
        ],
        "contexts": [
            [
                "軟體工程師面試通常包含三個部分：演算法題目、系統設計、行為問題。",
                "準備演算法面試時，建議在 LeetCode 上練習至少 150 題中等難度的題目。",
                "系統設計面試會考察候選人設計大規模分散式系統的能力。",
            ],
            [
                "轉職到科技業需要具備紮實的技術基礎，建議先選擇一個程式語言深入學習。",
                "建立個人專案作品集能夠展示你的實際開發能力，對求職很有幫助。",
                "參與開源專案可以累積實戰經驗，同時建立業界人脈。",
            ],
        ],
        "ground_truth": [
            "準備軟體工程師面試需要練習演算法、系統設計和行為面試三個方面。",
            "轉職科技業需要學習技術、建立作品集、參與社群活動。",
        ],
    }

    # Create dataset
    dataset = Dataset.from_dict(test_data)

    print("🚀 Starting RAGAS evaluation...")
    print(f"Dataset size: {len(dataset)} examples")
    print("Metrics: faithfulness, answer_relevancy, context_recall, context_precision")
    print()

    # Run evaluation
    try:
        result = evaluate(
            dataset,
            metrics=[
                faithfulness,
                answer_relevancy,
                context_recall,
                context_precision,
            ],
        )

        print("✅ RAGAS evaluation completed!")
        print()
        print("=" * 60)
        print("EVALUATION RESULTS")
        print("=" * 60)

        # Convert to pandas first to access data
        df = result.to_pandas()

        # Calculate average for each metric
        metrics = [
            "faithfulness",
            "answer_relevancy",
            "context_recall",
            "context_precision",
        ]
        for metric_name in metrics:
            if metric_name in df.columns:
                avg_value = df[metric_name].mean()
                print(f"{metric_name:20s}: {avg_value:.4f}")

        print("=" * 60)
        print()
        print(f"✅ Evaluation successful! Tested {len(df)} samples.")
        print()

        return result

    except Exception as e:
        print(f"❌ Error during evaluation: {str(e)}")
        import traceback

        traceback.print_exc()
        raise


async def test_ragas_with_real_data():
    """Test RAGAS with data from actual database"""
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session

    from app.core.config import settings
    from app.models.document import Chunk, Document
    from app.services.openai_service import OpenAIService

    print("🔍 Testing RAGAS with real database data...")

    # Create database connection
    engine = create_engine(settings.DATABASE_URL)

    with Session(engine) as db:
        # Get a sample document
        stmt = select(Document).limit(1)
        result = db.execute(stmt)
        document = result.scalar_one_or_none()

        if not document:
            print("⚠️  No documents found in database. Please upload a PDF first.")
            return

        print(f"Using document: {document.title}")

        # Get chunks for this document
        stmt = select(Chunk).where(Chunk.doc_id == document.id).limit(5)
        result = db.execute(stmt)
        chunks = result.scalars().all()

        if not chunks:
            print("⚠️  No chunks found for this document.")
            return

        print(f"Found {len(chunks)} chunks")

        # Create a simple test question
        openai_service = OpenAIService()
        sample_context = [chunk.text for chunk in chunks[:3]]

        # Generate answer using the chunks as context
        question = "請根據文件內容，說明主要重點是什麼？"
        context_text = "\n\n".join(sample_context)
        prompt = f"根據以下內容回答問題：\n\n{context_text}\n\n問題：{question}"

        answer = await openai_service.chat_completion(
            [{"role": "user", "content": prompt}]
        )

        # Prepare RAGAS dataset
        from datasets import Dataset

        test_data = {
            "question": [question],
            "answer": [answer],
            "contexts": [sample_context],
        }

        dataset = Dataset.from_dict(test_data)

        # Evaluate
        from ragas import evaluate
        from ragas.metrics import answer_relevancy, faithfulness

        result = evaluate(
            dataset,
            metrics=[faithfulness, answer_relevancy],
        )

        print()
        print("=" * 60)
        print("REAL DATA EVALUATION RESULTS")
        print("=" * 60)

        # Convert to pandas and extract metrics
        df = result.to_pandas()
        for metric_name in ["faithfulness", "answer_relevancy"]:
            if metric_name in df.columns:
                avg_value = df[metric_name].mean()
                print(f"{metric_name:20s}: {avg_value:.4f}")

        print("=" * 60)
        print()
        print(f"Question: {question}")
        print(f"Answer: {answer[:200]}...")

        return result


async def main():
    """Run all tests"""
    print("=" * 60)
    print("RAGAS FUNCTIONALITY TEST")
    print("=" * 60)
    print()

    # Test 1: Basic functionality with sample data
    print("TEST 1: Basic RAGAS evaluation with sample data")
    print("-" * 60)
    await test_ragas_basic()

    print()
    print()

    # Test 2: Real data from database (optional)
    print("TEST 2: RAGAS evaluation with real database data")
    print("-" * 60)
    try:
        await test_ragas_with_real_data()
    except Exception as e:
        print(f"⚠️  Skipping real data test: {str(e)}")

    print()
    print("✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
