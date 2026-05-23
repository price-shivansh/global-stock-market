import asyncio
from core.quant_engine import quant_engine

async def main():
    print("Testing generate_ai_summary for CL=F")
    summary = await quant_engine.generate_ai_summary("CL=F")
    print(summary.model_dump_json(indent=2))

if __name__ == "__main__":
    asyncio.run(main())
