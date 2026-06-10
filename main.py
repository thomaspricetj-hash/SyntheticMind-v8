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

        # ---------------------------------------------------------
        # TEST MODE — forces fast-path reasoning
        # Usage:
        #   test: 2+2
        #   test: reason deeply..., intent=conversation
        # ---------------------------------------------------------
        if user.startswith("test:"):
            payload = user[len("test:"):].strip()

            # Default: fast-path reasoning
            intent = "small_reasoning"

            # Optional override: "test: something, intent=xyz"
            if ", intent=" in payload:
                payload, intent_part = payload.rsplit(", intent=", 1)
                intent = intent_part.strip() or "small_reasoning"

            result = runtime.generate(
                text=payload.strip(),
                intent=intent,
                user_id="local",
                session_id="local"
            )

            reply = result.get("reply") or result.get("output") or str(result)
            print(f"AI: {reply}\n")
            continue

        # ---------------------------------------------------------
        # NORMAL MODE — full conversation pipeline
        # ---------------------------------------------------------
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







