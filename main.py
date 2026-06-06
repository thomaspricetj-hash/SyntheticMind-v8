from bitdrop_core.ai.metamodel.runtime import MetaModelRuntime
import bitdrop_core.ai.metamodel.runtime as R

def main():
    # Debug: confirm which runtime.py is actually being loaded
    print(">>> USING RUNTIME FILE:", R.__file__)

    runtime = MetaModelRuntime()

    print("\nSyntheticMind v8 is online.")
    print("Type 'exit' to quit.\n")

    while True:
        user = input("You: ").strip()
        if user.lower() in ("exit", "quit", "bye"):
            print("Shutting down SyntheticMind...")
            break

        # Route ALL conversation through the REAL runtime pipeline
        result = runtime.generate(
            text=user,
            intent="conversation",
            user_id="local",
            session_id="local"
        )

        reply = result.get("reply") or result.get("output") or str(result)

        print(f"AI: {reply}\n")

if __name__ == "__main__":
    main()







