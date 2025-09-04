import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { ChatModel } from "../../generated";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function isLocalModel(model: ChatModel) {
  return !isCloudModel(model);
}

export function isCloudModel(model: ChatModel) {
  const cloudSet = new Set<string>([
    ChatModel.LLAMA_3_70B as unknown as string,
    ChatModel.GPT_4O as unknown as string,
    ChatModel.GPT_4O_MINI as unknown as string,
    "gemini-1.5-pro",
    "gemini-2.5-pro",
  ]);
  return cloudSet.has(model as unknown as string);
}
