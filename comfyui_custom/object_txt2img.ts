import { z } from "zod";
import config from "../config";

const ComfyNodeSchema = z.object({
  inputs: z.any(),
  class_type: z.string(),
  _meta: z.any().optional(),
});

type ComfyNode = z.infer<typeof ComfyNodeSchema>;

interface Workflow {
  RequestSchema: z.ZodObject<any, any>;
  generateWorkflow: (input: any) => Record<string, ComfyNode>;
  description?: string;
  summary?: string;
}

const DEFAULT_CHECKPOINT = "SSD-1B-A1111.safetensors";
const OBJECT_SUFFIX =
  "single isolated object render, centered composition, full object visible, object completely inside the frame, " +
  "small object in frame, plain light studio background, symmetrical product shot, no cropped edges, " +
  "architectural maquette, isolated building only, no site context, no street, no sidewalk, no trees, no plants, no ground plane, " +
  "no podium, no pedestal, no platform, no landscaping, floating cutout object, seamless backdrop, orthographic product render, " +
  "single standalone building, no neighboring buildings, no city block, no exterior environment, white seamless studio background";

const RequestSchema = z.object({
  prompt: z.string().describe("The positive prompt for image generation"),
  negative_prompt: z
    .string()
    .optional()
    .default(
      "cropped, close-up, busy background, city scene, room interior, multiple objects, text, watermark, " +
      "trees, plants, road, sidewalk, plaza, outdoor scene, background buildings, skyline, dramatic environment, ground plane, " +
      "podium, pedestal, platform, landscaping, grass, bushes, parked car, street furniture, cast shadow, diorama base, " +
      "neighboring buildings, city block, alley, street corner, urban context"
    )
    .describe("The negative prompt for image generation"),
  width: z
    .number()
    .int()
    .min(512)
    .max(1536)
    .optional()
    .default(1024)
    .describe("Width of the generated image"),
  height: z
    .number()
    .int()
    .min(512)
    .max(1536)
    .optional()
    .default(1024)
    .describe("Height of the generated image"),
  seed: z
    .number()
    .int()
    .optional()
    .default(() => Math.floor(Math.random() * 100000000000))
    .describe("Seed for random number generation"),
  steps: z
    .number()
    .int()
    .min(1)
    .max(100)
    .optional()
    .default(20)
    .describe("Number of sampling steps"),
  cfg_scale: z
    .number()
    .min(0)
    .max(20)
    .optional()
    .default(9)
    .describe("Classifier-free guidance scale"),
  sampler_name: config.samplers
    .optional()
    .default("euler")
    .describe("Name of the sampler to use"),
  scheduler: config.schedulers
    .optional()
    .default("normal")
    .describe("Type of scheduler to use"),
  denoise: z
    .number()
    .min(0)
    .max(1)
    .optional()
    .default(1)
    .describe("Denoising strength"),
  checkpoint: z
    .string()
    .optional()
    .default(DEFAULT_CHECKPOINT)
    .describe("Checkpoint filename inside the mounted ComfyUI checkpoints folder"),
});

type InputType = z.infer<typeof RequestSchema>;

function generateWorkflow(input: InputType): Record<string, ComfyNode> {
  const positivePrompt = `${input.prompt}, ${OBJECT_SUFFIX}`;

  return {
    "3": {
      inputs: {
        seed: input.seed,
        steps: input.steps,
        cfg: input.cfg_scale,
        sampler_name: input.sampler_name,
        scheduler: input.scheduler,
        denoise: input.denoise,
        model: ["4", 0],
        positive: ["6", 0],
        negative: ["7", 0],
        latent_image: ["5", 0],
      },
      class_type: "KSampler",
      _meta: {
        title: "KSampler",
      },
    },
    "4": {
      inputs: {
        ckpt_name: input.checkpoint,
      },
      class_type: "CheckpointLoaderSimple",
      _meta: {
        title: "Load Checkpoint",
      },
    },
    "5": {
      inputs: {
        width: input.width,
        height: input.height,
        batch_size: 1,
      },
      class_type: "EmptyLatentImage",
      _meta: {
        title: "Empty Latent Image",
      },
    },
    "6": {
      inputs: {
        text: positivePrompt,
        clip: ["4", 1],
      },
      class_type: "CLIPTextEncode",
      _meta: {
        title: "CLIP Text Encode (Prompt)",
      },
    },
    "7": {
      inputs: {
        text: input.negative_prompt,
        clip: ["4", 1],
      },
      class_type: "CLIPTextEncode",
      _meta: {
        title: "CLIP Text Encode (Negative Prompt)",
      },
    },
    "8": {
      inputs: {
        samples: ["3", 0],
        vae: ["4", 2],
      },
      class_type: "VAEDecode",
      _meta: {
        title: "VAE Decode",
      },
    },
    "9": {
      inputs: {
        filename_prefix: "ComfyUI",
        images: ["8", 0],
      },
      class_type: "SaveImage",
      _meta: {
        title: "Save Image",
      },
    },
  };
}

const workflow: Workflow = {
  RequestSchema,
  generateWorkflow,
  summary: "Centered Object Text to Image",
  description: "Generate a centered single-object image suitable for downstream 3D reconstruction.",
};

export default workflow;
