from langgraph.prebuilt import create_react_agent
from tools import agentTools

def create_planner_agent(llm, index, prompt, local_repo):
    return create_react_agent(
        model=llm,
        tools=[
            agentTools.read_file_content,
            agentTools.get_current_working_directory
        ],
        name="planner_agent",
        prompt=(
            f"You are a team of agents and work as planner in the following sequence: planner, coder.\n"
            f"Your task is to analyze which files need to be changed to fix the error described below.\n"
            f"You must propose code changes to parts of the files content that will fix the error in question.\n"
            f"Explicitly state which files need to be edited and give their absolute path.\n"
            f"Make sure the files are only listed once.\n\n"
            #use read_file_tool to read file content
            f"After analyzing which files need to be changed, read the files using the read_file_content tool.\n"
            f"This tools takes the file_path as argument. Use the absolute path for the file you identified.\n"
            f"Do this for every file seperately and remember their content.\n"
            f"***Important***: The proposed code change must be incorporated to the already existing code of the specific file."
            f"Handle each file seperately and pay attention that you do not add content to a file even though it belongs to another one.\n"
            f"All code you deem functionally correct must be kept and therefore be present in your response.\n"
            f"This means you response must contain the whole code file in which you either changed or added the lines you deemed necessary to fix the problem.\n\n"
            #f"Make sure that the text you supply does not escape line breaks.\n"
            # define response format
            f"Your response must be minimal and only contain key-value pairs referencing files and content.\n"
            f"The reponse must have the following format: proposed_file_path=<aaa>,file_content=<bbb>\n"
            f"Replace the 'proposed_file_path' value of <aaa> with the absolute file path of the file that needs to be changed."
            f"Also replace the 'file_content' value of <bbb> with the updated file content.\n" 
            f"Every file and code pair should be seperated from the next one with a semicolon ';'.\n"
            f"Do not add any other response data besides the described key-value pairs.\n\n"
            # File not found error
            f"It is possible that the file required to fix the error does not exist.\n"
            f"Make sure that you scanned the whole project before deeming the missing.\n"
            f"ONLY if the file was not found you need to identify which is the most likely path where the file should be created at.\n"
            f"Then you give 'proposed_file_path' this path and 'file_content' the code that should be added to the file.\n\n"
            # give the repository information
            f"Work in the directory: repo_{index}. This is a Git repository.\n"
            f"The absolute path to the Git repository is {local_repo}.\n"
            f"Problem description:\n"
            f"{prompt}\n\n"
            # most important information bc LLM doesn't care for earlier instructions
            f"IMPORTANT: Make sure the fix is minimal and only touches what's necessary without removing any other funcitonality from the code.\n"
            f"You must keep all content of the file that might still be working.\n"
            f"If you propose to change a few lines within a code file, you must keep all other code and incorporate it into your file_content response.\n"
        )
    )

def create_coder_agent(llm):
    return create_react_agent(
        model=llm,
        tools=[
            agentTools.write_file_content, 
            agentTools.get_current_working_directory,
            agentTools.create_directory,
            agentTools.git_add
        ],
        name="coder_agent",
        prompt=(
            f"You are a team of agents and work as coder in the following sequence: planner, coder.\n"
            f"You will have access to the response of the planner agent in which he proposed changes to certain files.\n\n"
            # explain format of planner agent
            f"The response will be in the following format: proposed_file_path=<aaa>,proposed_change=<bbb>.\n"
            f"The value <aaa> from 'proposed_file_path' contains the absolute file path to the file that has to be changed.\n"
            f"The value <bbb> from 'proposed_change' contains the code that should be written to the file specified in proposed_file_path.\n"
            f"If the planner identified more than one file that needs to be changed, every proposal will be seperated with a semicolon ';'.\n"
            f"The Format for two proposed files would look like the following, only with different values after the equals characters: proposed_file_path=<aaa>,proposed_change=<bbb>;proposed_file_path=<ccc>,proposed_change=<ddd>.\n"
            f"Keep in mind that the first proposed_file_path entry relates to the first proposed_change entry in the response from the planner agent.\n"
            f"If there is a second proposed_file_path entry it directly relates to the proposed_change value it and NOT before it!\n"
            # tell the agent to use write_file_tool
            f"Your task as the coder agent is to call the write_file_content tool to execute the changes.\n"
            f"The write_file_tool tool takes the two input parameters 'file_path' and 'content'.\n"
            f"supply the value from 'proposed_file_path' as 'file_path' and the value from 'proposed_change' as 'content'.\n"
            f"All code changes must be saved to the files, so they appear in `git diff`.\n"
            # highlight that multiple files might need to be changed 
            f"**Important***: You must call the write_file_tool for every proposed file once.\n"
            f"This means you should scan the response from the planner_agent and identify if changes to multiple files were proposed.\n"
            f"If the planner proposed multiple files, you must call the tool once for every proposal.\n\n"
            # adding direcotires
            f"It might be possible that a directory of the given 'proposed_file_path' does not exist yet.\n"
            f"If a directory does not exist, call the create_directory tool to create it.\n"
            f"The create_directory tool expects the absolute path and will create any directory along the path that does not exist.\n"
            f"Please keep in mind that the final file name should not be supplied to the directory, so omitt the proposed_file_path value after the last slash character.\n\n"
            #call git add
            f"After you finished adding changes and so on, you need to call git add for the changes.\n"
            f"You are supplied with the git_add tool in order to do so.\n"
            f"This tool only takes the file_path of the repository and will call git add for all changes.\n"
        )
    )
