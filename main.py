from langgraph_supervisor import create_supervisor
from langchain_openai import ChatOpenAI
from tools import tools
import json
import os
import asyncio
import re
import agents

API_URL = "http://localhost:8081/task/index/"
LOG_FILE = "results.log"

mini_llm = ChatOpenAI(
    base_url="http://188.245.32.59:4000/v1",
    model="gpt-4o-mini",
    temperature=0.1
)

main_llm = ChatOpenAI(
    base_url="http://188.245.32.59:4000/v1",
    model="gpt-4o",
    temperature=0.1
)

async def run_agents(index):
    api_url = f"{API_URL}{index}"
    print(f"fetching test case {index} from {api_url}...")
    #local_repo = os.path.join(config.workspace_root, f"repo_{index}")
    local_repo = os.path.join(os.getcwd(), f"repos/repo_{index}")
    local_repo = local_repo.replace("\\", '/')
    work_dir = os.getcwd()

    try:
        testcase = tools.fetch_test_case(api_url)
        prompt = testcase["Problem_statement"]
        git_clone = testcase["git_clone"]
        fail_tests = json.loads(testcase.get("FAIL_TO_PASS", "[]"))
        pass_tests = json.loads(testcase.get("PASS_TO_PASS", "[]"))
        instance_id = testcase["instance_id"]
        try:
            tools.clone_repo(git_clone, local_repo)
        except Exception as e:
            print(f"Git repo is already cloned")
        
        planner_agent = agents.create_planner_agent(mini_llm, index, prompt, local_repo)
        coder_agent = agents.create_coder_agent(mini_llm)

        # Create supervisor workflow
        workflow = create_supervisor(
                [planner_agent, coder_agent],
                model=mini_llm,
                #tools=[],
                prompt=(
                    f"You are the supervisor of a planner and a coder agent.\n"
                    f"You are supposed to call the planner first and then delegate its findings to the coder agent.\n"
                    f"The coder agent takes the response of the planner agent to identify files and makes changes to those files.\n"
                )
            )

        # Compile and run
        app = workflow.compile()
        result = app.invoke({
            "messages": [
                {
                    "role": "user",
                    "content": "analyze the code error, propose a solution to fix this error so that the coder agent can make the necessary changes to the files."
                }
            ]
        },
        {
            "recursion_limit": 100
        })

        #tools.git_add_and_commit(local_repo, "add all files")

        print(f"\n{result}\n")
        
        # total_tokens is given after each agent step to show how many tokens it used
        # set() to remove duplicates, response lists all total_tokens values two times
        all_total_tokens_str = set(re.findall(r"'total_tokens': (\d+)", str(result["messages"])))

        # # Convert the extracted strings to integers and sum them up
        total_sum = sum(int(token_str) for token_str in all_total_tokens_str)

        #Call REST service instead for evaluation changes form agent
        print(f"Calling SWE-Bench REST service with repo: {local_repo}")
        test_payload = {
            "instance_id": instance_id,
            "repoDir": f"/repos/repo_{index}", #mount with docker
            "FAIL_TO_PASS": fail_tests,
            "PASS_TO_PASS": pass_tests,
        }
        #print(f"test_payload: {test_payload}")
        result_json = tools.verify_solution(test_payload)
        #print(f"result_json:\n{result_json}")
        tools.log_results(result_json, work_dir, LOG_FILE, index, total_sum)
        

    except Exception as e:
        os.chdir(work_dir)
        with open(LOG_FILE, "a", encoding="utf-8") as log:
            log.write(f"\n--- TESTCASE {index} ---\n")
            log.write(f"Error: {e}")
        print(f"Error in test case {index}: {e}")


async def main():
    for i in range(1,31):
        await run_agents(i)

if __name__ == "__main__":
    asyncio.run(main())