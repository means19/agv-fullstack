import { useToast } from "@/hooks/use-toast";
import {
  useForm,
  type Resolver,
  type FieldErrors,
  type DefaultValues,
} from "react-hook-form";
import { z } from "zod";

interface UseFormDialogOptions<T> {
  defaultValues: DefaultValues<T>;
  schema: z.ZodSchema;
  onSubmit: (values: T) => Promise<void>;
  successMessage: string;
  errorMessage: string;
  onSuccess?: () => void;
}

export function useFormDialog<T extends Record<string, unknown>>({
  defaultValues,
  schema,
  onSubmit,
  successMessage,
  errorMessage,
  onSuccess,
}: UseFormDialogOptions<T>) {
  const { toast } = useToast();

  // Create the resolver function separately with the correct type
  const zodResolver: Resolver<T> = async (data) => {
    try {
      const validatedData = await schema.parseAsync(data);
      return {
        values: validatedData as T,
        errors: {},
      };
    } catch (error) {
      if (error instanceof z.ZodError) {
        const errors = error.errors.reduce<FieldErrors<T>>(
          (acc, curr) => {
            const path = curr.path.join(".");
            return {
              ...acc,
              [path]: { message: curr.message, type: "validation" },
            };
          },
          {} as FieldErrors<T>,
        );
        return {
          values: {} as Record<string, never>,
          errors,
        };
      }
      return {
        values: {} as Record<string, never>,
        errors: { root: { type: "validation", message: "Invalid form data" } } as FieldErrors<T>,
      };
    }
  };

  const form = useForm<T>({
    resolver: zodResolver,
    defaultValues,
    mode: "onChange",
  });

  const handleSubmit = async (values: T) => {
    try {
      await onSubmit(values);
      toast({
        title: successMessage,
        description: JSON.stringify(values, null, 2),
      });
      onSuccess?.();
    } catch (error) {
      console.error("Form submission error:", error);
      toast({
        title: errorMessage,
        description:
          error instanceof Error ? error.message : "Unknown error occurred",
      });
    }
  };

  return {
    form,
    handleSubmit: form.handleSubmit(handleSubmit),
  };
}
